from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

import uuid
import enum

from app.models.base import Base


class OrgType(str, enum.Enum):
    HQ = "HQ"          # 总部
    BRANCH = "BRANCH"  # 分公司
    TEAM = "TEAM"      # 团队/部门


class Organization(Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="组织名称",
    )
    type: Mapped[OrgType] = mapped_column(
        SAEnum(OrgType, name="org_type", length=20),
        nullable=False,
        default=OrgType.TEAM,
        comment="组织类型",
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        comment="上级组织ID",
    )

    # 关系
    parent: Mapped["Organization | None"] = relationship(  # noqa: F821
        "Organization",
        remote_side="Organization.id",
        lazy="selectin",
    )
    children: Mapped[list["Organization"]] = relationship(  # noqa: F821
        "Organization",
        back_populates="parent",
        lazy="selectin",
    )
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User",
        back_populates="organization",
        foreign_keys="[User.organization_id]",
        lazy="selectin",
    )
