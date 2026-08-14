from datetime import datetime, timezone
import uuid

from sqlalchemy import String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    phone: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="手机号",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="姓名",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="密码哈希（演示模式可为空）",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="头像URL",
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        comment="角色ID",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="所属组织ID",
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        comment="所属团队ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        server_default="active",
        nullable=False,
        comment="状态：active / disabled",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间",
    )
    demo_mode: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="是否为演示用户",
    )

    # 关系
    role: Mapped["Role"] = relationship(  # noqa: F821
        "Role",
        back_populates="users",
        lazy="joined",
    )
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="users",
        foreign_keys=[organization_id],
        lazy="joined",
    )
    team: Mapped["Organization | None"] = relationship(  # noqa: F821
        "Organization",
        foreign_keys=[team_id],
        lazy="joined",
    )

    @property
    def role_code(self) -> str:
        return self.role.code if self.role else ""

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else ""
