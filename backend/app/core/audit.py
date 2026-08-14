"""审计日志中间件 —— 自动记录关键操作。"""
import re

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from structlog import get_logger

logger = get_logger()


# 需要审计的路径前缀（POST/PUT/DELETE 或特定路径）
AUDITABLE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
AUDITABLE_PATHS = {"/auth/login", "/auth/refresh"}
SKIP_PATHS = {"/health", "/ready"}

# 资源类型映射
_RESOURCE_PATTERN = re.compile(r"/api/v1/(\w+)")
_UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# 路径 -> 资源类型映射
_RESOURCE_TYPE_MAP: dict[str, str] = {
    "customers": "customers",
    "scripts": "scripts",
    "training": "training",
    "community": "community",
    "admin": "admin",
    "knowledge": "knowledge",
    "auth": "auth",
    "ai": "ai",
}


def _extract_resource_info(path: str) -> tuple[str, str | None]:
    """从路径中推断资源类型和资源 ID。

    Returns:
        (resource_type, resource_id or None)
    """
    # 查找路径中的 UUID
    resource_id = None
    uuid_match = _UUID_PATTERN.search(path)
    if uuid_match:
        resource_id = uuid_match.group()

    # 推断资源类型
    resource_type = "unknown"
    match = _RESOURCE_PATTERN.match(path)
    if match:
        segment = match.group(1)
        resource_type = _RESOURCE_TYPE_MAP.get(segment, segment)

    return resource_type, resource_id


def _get_client_ip(request: Request) -> str:
    """从请求中提取客户端 IP。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def _should_audit(method: str, path: str) -> bool:
    """判断是否需要审计该请求。"""
    # 跳过健康检查
    if any(path.endswith(skip) for skip in SKIP_PATHS):
        return False
    # POST/PUT/DELETE/PATCH 始终审计
    if method in AUDITABLE_METHODS:
        return True
    # 特定路径审计（如 GET /auth/login 不存在，但 login 是 POST）
    for audit_path in AUDITABLE_PATHS:
        if audit_path in path:
            return True
    return False


async def write_audit_to_db(audit_data: dict) -> None:
    """将审计数据写入数据库（Phase 5 通过 Repository 实现持久化）。

    当前仅通过 structlog 记录，真正的 DB 持久化在 Phase 5 实现。
    """
    logger.info(
        "audit_log_db_pending",
        **audit_data,
    )


class AuditMiddleware(BaseHTTPMiddleware):
    """审计日志中间件 —— 自动记录关键操作。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        method = request.method
        path = request.url.path

        if not _should_audit(method, path):
            return response

        resource_type, resource_id = _extract_resource_info(path)

        # 尝试获取用户信息
        user_id = None
        try:
            user_id = str(request.state.user.id) if hasattr(request.state, "user") else None
        except Exception:
            pass

        request_id = getattr(request.state, "request_id", None)

        audit_data = {
            "action": f"api.{method}.{path}",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "ip_address": _get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "request_id": request_id,
            "status_code": response.status_code,
            "detail": f"{method} {path}",
        }

        try:
            logger.info("audit_log", **audit_data)
            await write_audit_to_db(audit_data)
        except Exception as exc:
            # 审计失败不应影响正常响应
            logger.warning("audit_log_error", error=str(exc))

        return response
