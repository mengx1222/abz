from sqlalchemy import String, Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


# 多对多关联表
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class RolePermission:
    """用于 type hint 的辅助类，实际使用 role_permissions 表。"""
    pass


class Permission(Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="权限编码，如 customer:read",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="权限名称",
    )
    module: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="所属模块",
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="权限描述",
    )

    # 关系
    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )
