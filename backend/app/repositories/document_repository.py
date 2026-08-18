"""文档仓储层（Task 22 — Document Management Production 化）。

集中管理 Document 的数据库访问（SQLAlchemy async）。
权限语义沿用 Task 17B/21（不重新设计）：
- 可见性：Document 继承所属 KnowledgeBase 的权限（JOIN KnowledgeBase）——
  角色：KB.allowed_roles IS NULL（全员）OR 包含当前角色；
  组织：KB.organization_id IS NULL（共享）OR IN (accessible_org_ids)
- 删除为物理删除：documents FK ondelete=CASCADE 级联清理 document_chunks
  （embedding 在 chunk 行内一并删除，不留孤儿数据）
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document, DocumentChunk, KnowledgeBase
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """文档 CRUD 仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    # ---- 可见性过滤（继承 KB 权限） ----
    def _visibility_join(self, user_roles: list[str] | None, accessible_org_ids: list[str] | None):
        """构造 JOIN KnowledgeBase + 可见性条件。返回 (join_condition_list, where_condition_list)。"""
        conds = []
        if user_roles:
            role_conds = [KnowledgeBase.allowed_roles.is_(None)]
            for role in user_roles:
                role_conds.append(KnowledgeBase.allowed_roles.op("?")(role))
            conds.append(or_(*role_conds))
        if accessible_org_ids and "__ALL__" not in accessible_org_ids:
            org_ids = []
            for oid in accessible_org_ids:
                if not oid:
                    continue
                try:
                    org_ids.append(uuid.UUID(oid))
                except (ValueError, TypeError):
                    continue
            if org_ids:
                conds.append(
                    or_(
                        KnowledgeBase.organization_id.is_(None),
                        KnowledgeBase.organization_id.in_(org_ids),
                    )
                )
        return conds

    # ---- 查询 ----
    async def create_document(
        self,
        knowledge_base_id: uuid.UUID,
        title: str,
        file_name: str | None = None,
        file_type: str = "txt",
        file_size: int = 0,
        content_text: str | None = None,
        status: str = "uploaded",
        metadata_: dict | None = None,
        created_by: uuid.UUID | None = None,
        published_at: datetime | None = None,
    ) -> Document:
        """创建文档（DB insert）。"""
        doc = Document(
            knowledge_base_id=knowledge_base_id,
            title=title,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            content_text=content_text,
            status=status,
            metadata_=metadata_,
            created_by=created_by,
            published_at=published_at,
            chunk_count=0,
            version_number=1,
        )
        self.session.add(doc)
        await self.session.flush()
        await self.session.refresh(doc)
        return doc

    async def get_document(
        self,
        doc_id: uuid.UUID,
        kb_id: uuid.UUID | None = None,
        user_roles: list[str] | None = None,
        accessible_org_ids: list[str] | None = None,
    ) -> Document | None:
        """按主键获取文档（JOIN KB 可见性过滤；越权/不存在 → None）。"""
        stmt = (
            select(Document)
            .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
            .where(Document.id == doc_id, Document.is_deleted == False)
        )
        if kb_id is not None:
            stmt = stmt.where(Document.knowledge_base_id == kb_id)
        for c in self._visibility_join(user_roles, accessible_org_ids):
            stmt = stmt.where(c)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_documents(
        self,
        kb_id: uuid.UUID,
        status: str | None = None,
        user_roles: list[str] | None = None,
        accessible_org_ids: list[str] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[Document], int]:
        """知识库下文档列表（DB query + 可见性过滤）。"""
        base = (
            select(Document)
            .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
            .where(Document.knowledge_base_id == kb_id, Document.is_deleted == False)
        )
        count_q = (
            select(func.count())
            .select_from(Document)
            .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
            .where(Document.knowledge_base_id == kb_id, Document.is_deleted == False)
        )
        if status:
            base = base.where(Document.status == status)
            count_q = count_q.where(Document.status == status)
        for c in self._visibility_join(user_roles, accessible_org_ids):
            base = base.where(c)
            count_q = count_q.where(c)
        total = (await self.session.execute(count_q)).scalar() or 0
        base = base.order_by(Document.created_at.desc())
        base = base.offset((page - 1) * page_size).limit(page_size)
        records = list((await self.session.execute(base)).scalars().all())
        return records, total

    async def update_document_status(
        self,
        doc_id: uuid.UUID,
        status: str,
        *,
        published_by: uuid.UUID | None = None,
        published_at: datetime | None = None,
        updated_by: uuid.UUID | None = None,
    ) -> Document | None:
        """更新文档状态（publish/unpublish 共用）。"""
        doc = await self.get_by_id(doc_id)
        if doc is None or doc.is_deleted:
            return None
        doc.status = status
        if published_at is not None:
            doc.published_at = published_at
        if published_by is not None:
            doc.published_by = published_by
        if updated_by is not None:
            doc.updated_by = updated_by
        await self.session.flush()
        await self.session.refresh(doc)
        return doc

    async def publish_document(
        self,
        doc_id: uuid.UUID,
        published_by: uuid.UUID | None = None,
    ) -> Document | None:
        """发布文档（status=published + published_at）。"""
        return await self.update_document_status(
            doc_id,
            "published",
            published_by=published_by,
            published_at=datetime.now(timezone.utc),
        )

    async def unpublish_document(
        self,
        doc_id: uuid.UUID,
        updated_by: uuid.UUID | None = None,
    ) -> Document | None:
        """取消发布（status=draft，保持已解析内容）。"""
        return await self.update_document_status(doc_id, "draft", updated_by=updated_by)

    async def delete_document(self, doc_id: uuid.UUID) -> bool:
        """物理删除文档（FK CASCADE 级联删 document_chunks/embedding）。"""
        doc = await self.get_by_id(doc_id)
        if doc is None or doc.is_deleted:
            return False
        await self.session.execute(delete(Document).where(Document.id == doc_id))
        await self.session.flush()
        return True
