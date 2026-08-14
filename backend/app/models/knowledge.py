"""知识库相关数据模型。

包含 KnowledgeBase（知识库）、Document（文档）、DocumentChunk（文档分块）。
遵循 database.md 中的表定义规范。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KnowledgeBase(Base):
    """知识库 —— 知识文档的逻辑容器。"""

    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="知识库名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="知识库描述")
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="product", comment="分类：product/regulation/training/faq"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", comment="状态：draft/active/archived"
    )
    document_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="文档数量"
    )
    total_chunks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="总分块数量"
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", comment="是否公开（全员可见）"
    )
    allowed_roles: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment="允许访问的角色列表，null表示全员"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1", comment="版本号"
    )
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="生效日期")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="失效日期")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="创建人")
    # ---- 关系 ----
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="knowledge_base", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase id={self.id} name={self.name!r} status={self.status!r}>"


class Document(Base):
    """文档 —— 知识库中的一份文件。"""

    __tablename__ = "documents"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="文档标题")
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="原始文件名")
    file_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="txt", comment="文件类型：pdf/docx/txt/md"
    )
    file_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="文件大小(bytes)"
    )
    content_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="解析后的纯文本内容"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploaded",
        comment="状态：uploaded/parsing/parsed/reviewing/published/expired",
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="分块数量"
    )
    parse_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="解析错误信息"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发布时间"
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="发布人"
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, comment="扩展元数据"
    )
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="生效日期")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="失效日期")
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1", comment="版本号")
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="上一版本文档ID")
    # ---- 关系 ----
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase", back_populates="documents",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title!r} status={self.status!r}>"


class DocumentChunk(Base):
    """文档分块 —— 语义切分后的最小检索单元。"""

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属文档",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="分块序号（从0开始）"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="分块文本内容"
    )
    token_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="Token数量"
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536), nullable=True, comment="向量嵌入(1536维)"
    )
    search_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="用于BM25检索的纯文本（去除格式）"
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, comment="分块元数据（heading, section等）"
    )
    # ---- 关系 ----
    document: Mapped["Document"] = relationship(
        "Document", back_populates="chunks",
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc={self.document_id} idx={self.chunk_index}>"
