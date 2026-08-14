from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Role(Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="角色编码，如 admin / sales / manager",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="角色名称",
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="角色描述",
    )
    level: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        comment="角色级别（数字越大权限越高）",
    )

    # 关系
    permissions: Mapped[list["Permission"]] = relationship(  # noqa: F821
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User",
        back_populates="role",
        lazy="selectin",
    )
