"""话术相关数据模型。"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Script(Base):
    """话术 —— AI生成的销售话术。"""

    __tablename__ = "scripts"

    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="话术标题")
    customer_context: Mapped[dict | None] = mapped_column(
        "customer_context", JSONB, nullable=True, comment="客户上下文"
    )
    style: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="风格：affinity/professional/data_driven/concise"
    )
    content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="话术内容"
    )
    product_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="产品类型"
    )
    compliance_status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="green", comment="合规状态：green/yellow/red"
    )
    compliance_issues: Mapped[dict | None] = mapped_column(
        "compliance_issues", JSONB, nullable=True, comment="合规检查结果"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1", comment="版本号"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", comment="状态：draft/published/archived"
    )
    favorited_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="收藏数"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="使用次数"
    )

    def __repr__(self) -> str:
        title_preview = self.title[:30] if self.title else ""
        return f"<Script id={self.id} title={title_preview!r} style={self.style!r}>"


class ScriptVersion(Base):
    """话术版本。"""

    __tablename__ = "script_versions"

    script_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scripts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="版本号"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="版本内容")
    prompt_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="使用的Prompt版本"
    )
