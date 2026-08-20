"""审计日志 Repository —— AuditLog 落库与查询（Task 37，P1 B2）。

设计原则：
- 独立 session 使用（调用方传入），写失败不影响主业务（调用方捕获）。
- resource_id / user_id 统一归一化为 UUID（非 UUID 字符串降级为 None，避免落库报错）。
- action / resource_type 截断到列长度上限（String 50）。
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def _coerce_uuid(value) -> Optional[uuid.UUID]:
    """将值归一化为 UUID；无法解析时返回 None。"""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            return None
    return None


def _coerce_datetime(value: Optional[str]) -> Optional[datetime]:
    """解析 ISO 时间字符串；naive 视为 UTC。"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class AuditLogRepository:
    """审计日志数据访问层。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_log(
        self,
        *,
        user_id=None,
        organization_id=None,
        action: str,
        resource_type: str,
        resource_id=None,
        description: str = "",
        detail: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        status: str = "success",
    ) -> AuditLog:
        """创建一条审计日志（调用方负责 commit）。"""
        log = AuditLog(
            user_id=_coerce_uuid(user_id),
            organization_id=_coerce_uuid(organization_id),
            action=action[:50],
            resource_type=resource_type[:50],
            resource_id=_coerce_uuid(resource_id),
            description=(description or "")[:500],
            detail=detail,
            ip_address=(ip_address or "")[:50] or None,
            user_agent=(user_agent or "")[:500] or None,
            request_id=(request_id or "")[:36] or None,
            status=status[:20],
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_logs(
        self,
        *,
        user_id=None,
        organization_ids: Optional[list[str]] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        """按条件查询审计日志（倒序 + 分页）。返回 (items, total)。"""
        stmt = select(AuditLog)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == _coerce_uuid(user_id))
        if organization_ids:
            org_uuids = [u for u in (_coerce_uuid(x) for x in organization_ids) if u is not None]
            if org_uuids:
                stmt = stmt.where(AuditLog.organization_id.in_(org_uuids))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if start_time:
            stmt = stmt.where(AuditLog.created_at >= _coerce_datetime(start_time))
        if end_time:
            stmt = stmt.where(AuditLog.created_at <= _coerce_datetime(end_time))

        total = (
            await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()

        rows = (
            await self.session.execute(
                stmt.order_by(AuditLog.created_at.desc())
                .offset((max(page, 1) - 1) * max(page_size, 1))
                .limit(max(page_size, 1))
            )
        ).scalars().all()
        return list(rows), int(total)

    async def query_by_user(
        self, user_id, page: int = 1, page_size: int = 20
    ) -> tuple[list[AuditLog], int]:
        """按操作人查询。"""
        return await self.list_logs(user_id=user_id, page=page, page_size=page_size)

    async def query_by_resource(
        self, resource_type: str, resource_id, page: int = 1, page_size: int = 20
    ) -> tuple[list[AuditLog], int]:
        """按资源类型+资源ID查询。"""
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == _coerce_uuid(resource_id),
            )
            .order_by(AuditLog.created_at.desc())
            .offset((max(page, 1) - 1) * max(page_size, 1))
            .limit(max(page_size, 1))
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        total_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == _coerce_uuid(resource_id),
            )
        )
        total = (await self.session.execute(total_stmt)).scalar_one()
        return list(rows), int(total)
