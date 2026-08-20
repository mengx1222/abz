"""审计日志中间件 —— 自动记录关键操作。"""
import re
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from structlog import get_logger

from app.core.config import settings
from app.core.deps import async_session_factory
from app.repositories.audit_log_repository import AuditLogRepository

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


async def record_audit_log(
    *,
    user_id=None,
    action: str,
    resource_type: str,
    resource_id=None,
    description: str = "",
    detail: dict | None = None,
    status: str = "success",
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    """写审计日志（Task 37，P1 B2 落库实现）。

    - 生产模式：独立 session 持久化到 audit_logs 表；失败仅告警，**不影响主业务**。
    - Demo 模式：仅 structlog（与历史行为一致，不触碰 DB）。
    - 异步优先；调用方 await 后不抛异常。
    """
    if settings.DEMO_MODE:
        logger.info(
            "audit_log",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            user_id=str(user_id) if user_id else None,
            status=status,
        )
        return

    async with async_session_factory() as session:
        repo = AuditLogRepository(session)
        try:
            await repo.create_log(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                detail=detail,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                status=status,
            )
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.warning("audit_log_error", action=action, resource_type=resource_type, error=str(exc))


async def write_audit_to_db(audit_data: dict) -> None:
    """中间件钩子：将请求级审计数据持久化（Task 37 实现，替代原 structlog stub）。

    action 规范化：`api.POST./api/v1/...` 超出 String(50) 列长 → 转为 `{method}.{resource_type}`。
    status 按 status_code 判定 success/failure。
    """
    if settings.DEMO_MODE:
        logger.info("audit_log_db_pending", **audit_data)
        return

    raw_action = audit_data.get("action", "api.unknown")
    action = raw_action
    if action.startswith("api."):
        parts = action.split(".")
        method = parts[1].lower() if len(parts) > 1 else "unknown"
        resource_type = audit_data.get("resource_type") or "unknown"
        action = f"{method}.{resource_type}"

    status_code = audit_data.get("status_code", 0)
    detail = {"status_code": status_code}
    await record_audit_log(
        user_id=audit_data.get("user_id"),
        action=action,
        resource_type=audit_data.get("resource_type") or "unknown",
        resource_id=audit_data.get("resource_id"),
        description=audit_data.get("detail") or f"{action}",
        detail=detail,
        ip_address=audit_data.get("ip_address"),
        user_agent=audit_data.get("user_agent"),
        request_id=audit_data.get("request_id"),
        status="success" if int(status_code) < 400 else "failure",
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
