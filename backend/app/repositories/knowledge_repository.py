"""知识库仓储层（Task 21 — Production CRUD）。

集中管理 KnowledgeBase 的数据库访问（SQLAlchemy async）。
权限语义沿用 Task 17B（不重新设计）：
- 组织范围：organization_id IN (accessible_org_ids) OR organization_id IS NULL（共享）
- 角色范围：allowed_roles IS NULL（全员） OR allowed_roles 包含当前角色
- 删除为物理删除（FK ondelete=CASCADE 级联删除 documents/document_chunks）
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase
from app.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    """知识库 CRUD 仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(KnowledgeBase, session)

    async def create_knowledge_base(
        self,
        name: str,
        description: str = "",
        category: str = "product",
        is_public: bool = True,
        organization_id: uuid.UUID | None = None,
        allowed_roles: list[str] | None = None,
        metadata_: dict | None = None,
        created_by: uuid.UUID | None = None,
        status: str = "draft",
    ) -> KnowledgeBase:
        """创建知识库（DB insert）。"""
        kb = KnowledgeBase(
            name=name,
            description=description or None,
            category=category,
            status=status,
            is_public=is_public,
            organization_id=organization_id,
            allowed_roles=allowed_roles,
            metadata_=metadata_,
            created_by=created_by,
            version=1,
            document_count=0,
            total_chunks=0,
        )
        self.session.add(kb)
        await self.session.flush()
        await self.session.refresh(kb)
        return kb

    async def get_knowledge_base(
        self,
        kb_id: uuid.UUID,
        user_roles: list[str] | None = None,
        accessible_org_ids: list[str] | None = None,
    ) -> KnowledgeBase | None:
        """按主键获取知识库（带可见性过滤：角色 + 组织范围）。"""
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.is_deleted == False,
        )
        stmt = self._apply_visibility(stmt, user_roles, accessible_org_ids)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_knowledge_bases(
        self,
        category: str | None = None,
        status: str | None = None,
        user_roles: list[str] | None = None,
        accessible_org_ids: list[str] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[KnowledgeBase], int]:
        """知识库列表（DB query + 可见性过滤）。"""
        query = select(KnowledgeBase).where(KnowledgeBase.is_deleted == False)
        count_q = (
            select(func.count())
            .select_from(KnowledgeBase)
            .where(KnowledgeBase.is_deleted == False)
        )
        if category:
            query = query.where(KnowledgeBase.category == category)
            count_q = count_q.where(KnowledgeBase.category == category)
        if status:
            query = query.where(KnowledgeBase.status == status)
            count_q = count_q.where(KnowledgeBase.status == status)

        query = self._apply_visibility(query, user_roles, accessible_org_ids)
        count_q = self._apply_visibility(count_q, user_roles, accessible_org_ids)

        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.order_by(KnowledgeBase.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        records = list((await self.session.execute(query)).scalars().all())
        return records, total

    async def update_knowledge_base(
        self,
        kb_id: uuid.UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        status: str | None = None,
        is_public: bool | None = None,
        metadata_: dict | None = None,
        updated_by: uuid.UUID | None = None,
    ) -> KnowledgeBase | None:
        """更新知识库（DB update，version +1）。"""
        kb = await self.get_by_id(kb_id)
        if kb is None or kb.is_deleted:
            return None
        if name is not None:
            kb.name = name
        if description is not None:
            kb.description = description
        if category is not None:
            kb.category = category
        if status is not None:
            kb.status = status
        if is_public is not None:
            kb.is_public = is_public
        if metadata_ is not None:
            kb.metadata_ = metadata_
        kb.version = (kb.version or 1) + 1
        if updated_by is not None:
            kb.updated_by = updated_by
        await self.session.flush()
        await self.session.refresh(kb)
        return kb

    async def delete_knowledge_base(self, kb_id: uuid.UUID) -> bool:
        """物理删除知识库（FK CASCADE 级联删除 documents/document_chunks）。

        返回是否删除成功。
        """
        kb = await self.get_by_id(kb_id)
        if kb is None or kb.is_deleted:
            return False
        await self.session.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
        await self.session.flush()
        return True

    async def name_exists(
        self,
        name: str,
        organization_id: uuid.UUID | None,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """同名知识库检查（同组织/共享范围内）。"""
        stmt = select(KnowledgeBase.id).where(
            KnowledgeBase.name == name,
            KnowledgeBase.is_deleted == False,
        )
        if exclude_id is not None:
            stmt = stmt.where(KnowledgeBase.id != exclude_id)
        if organization_id is not None:
            stmt = stmt.where(
                or_(
                    KnowledgeBase.organization_id == organization_id,
                    KnowledgeBase.organization_id.is_(None),
                )
            )
        else:
            stmt = stmt.where(KnowledgeBase.organization_id.is_(None))
        existing = (await self.session.execute(stmt)).scalars().first()
        return existing is not None

    # ---- 内部工具 ----
    def _apply_visibility(self, stmt, user_roles: list[str] | None, accessible_org_ids: list[str] | None):
        """应用 Task 17B 可见性语义（角色 + 组织范围）。"""
        conds = []
        if user_roles:
            role_conds = [KnowledgeBase.allowed_roles.is_(None)]
            for role in user_roles:
                role_conds.append(KnowledgeBase.allowed_roles.has_key(role))
            conds.append(or_(*role_conds))
        if accessible_org_ids:
            org_conds = [KnowledgeBase.organization_id.is_(None)]
            org_conds.append(KnowledgeBase.organization_id.in_(accessible_org_ids))
            conds.append(or_(*org_conds))
        for c in conds:
            stmt = stmt.where(c)
        return stmt
