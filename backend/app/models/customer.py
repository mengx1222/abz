"""客户360相关数据模型。

包含 Customer（客户）、CustomerTag（客户标签）、
CustomerInteraction（互动记录）、CustomerFollowup（跟进任务）。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Customer(Base):
    """客户 —— 核心客户信息。"""

    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="客户姓名")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="年龄")
    gender: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="性别：male/female"
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="手机号")
    customer_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="prospective",
        comment="客户类型：prospective/active/lapsed",
    )
    tags: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment="标签ID列表"
    )
    insurance_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="感兴趣的保险类型"
    )
    current_stage: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="initial_contact",
        comment="销售阶段：initial_contact/needs_analysis/proposal/presentation/negotiation/closed_won/closed_lost",
    )
    intention_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, comment="意向等级 1-5"
    )
    source_channel: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="来源渠道"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="负责代理人",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属组织",
    )
    # ---- 关系 ----
    interactions: Mapped[list["CustomerInteraction"]] = relationship(
        "CustomerInteraction", back_populates="customer", lazy="selectin",
        cascade="all, delete-orphan",
    )
    followups: Mapped[list["CustomerFollowup"]] = relationship(
        "CustomerFollowup", back_populates="customer", lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.name!r} type={self.customer_type!r}>"


class CustomerTag(Base):
    """客户标签定义。"""

    __tablename__ = "customer_tags"

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="标签名称")
    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="标签分类"
    )

    def __repr__(self) -> str:
        return f"<CustomerTag id={self.id} name={self.name!r}>"


class CustomerInteraction(Base):
    """客户互动记录。"""

    __tablename__ = "customer_interactions"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="客户ID",
    )
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="互动类型：phone/wechat/f2f/email/other",
    )
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="outbound",
        comment="方向：inbound/outbound",
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="互动内容")
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True, comment="互动结果")
    next_followup_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="下次跟进日期"
    )
    # ---- 关系 ----
    customer: Mapped["Customer"] = relationship("Customer", back_populates="interactions")

    def __repr__(self) -> str:
        return f"<CustomerInteraction id={self.id} customer={self.customer_id} type={self.type!r}>"


class CustomerFollowup(Base):
    """客户跟进任务。"""

    __tablename__ = "customer_followups"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="客户ID",
    )
    scheduled_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="计划跟进日期"
    )
    completed_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="实际完成日期"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="状态：pending/completed/cancelled",
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="跟进内容")
    result: Mapped[str | None] = mapped_column(Text, nullable=True, comment="跟进结果")
    # ---- 关系 ----
    customer: Mapped["Customer"] = relationship("Customer", back_populates="followups")

    def __repr__(self) -> str:
        return f"<CustomerFollowup id={self.id} customer={self.customer_id} status={self.status!r}>"
