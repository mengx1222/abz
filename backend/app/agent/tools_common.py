"""AI Sales Agent —— 工具共享辅助（RAG 权限上下文构建）。"""
from __future__ import annotations

from typing import Any

from structlog import get_logger

logger = get_logger()


async def _build_rag_permission_context(user: Any, db: Any) -> dict[str, Any]:
    """构建 RAG 检索的权限上下文（角色 + 组织范围，复用 DataPermissionChecker）。

    与 script_service._production_generate_scripts 同语义：
    - 加载失败/无法确认权限 → roles=[]（全拒，RAG 走 REFUSE，不降级到通用知识）
    """
    roles: list[str] | None = None
    org_id: str | None = None
    accessible_org_ids: list[str] | None = None
    try:
        from sqlalchemy import select as sa_select

        from app.core.authorization import DataPermissionChecker
        from app.models.user import User as UserModel

        # user 可能已由 get_current_user eager-load；此处按需重新查询以确保组织树可用
        if user is not None and getattr(user, "id", None):
            user_row = (
                await db.execute(sa_select(UserModel).where(UserModel.id == user.id))
            ).scalar_one_or_none()
        else:
            user_row = None
        if user_row is not None:
            checker = DataPermissionChecker(user_row)
            roles = [user_row.role_code] if user_row.role_code else []
            org_id = str(user_row.organization_id)
            accessible_org_ids = checker.filter_accessible_org_ids()
        else:
            roles = []
    except Exception as e:  # noqa: BLE001
        logger.warning("agent_rag_permission_context_failed", error=str(e))
        roles = []
    return {"roles": roles, "org_id": org_id, "accessible_org_ids": accessible_org_ids}
