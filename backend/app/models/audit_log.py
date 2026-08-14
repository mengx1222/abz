"""审计日志模型：AuditLog（系统操作审计追踪）。"""
import uuid

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """系统审计日志 —— 记录关键业务操作。

    覆盖: 用户管理、权限变更、数据导出、合规操作、
    知识库管理、话术审批、社区管理等。
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="操作人ID",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="操作动作: create/update/delete/disable/enable/login/logout/export/approve/reject/pin/recommend",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="资源类型: user/customer/script/post/training_scenario/knowledge_base/compliance_rule/system",
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="资源ID",
    )
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="操作描述",
    )
    detail: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default="{}",
        comment="操作详情（变更前后的 diff）",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="IP 地址",
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="用户代理",
    )
    request_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="请求ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="success",
        comment="操作结果: success/failure",
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r} resource={self.resource_type!r}>"
