"""AI 陪练 —— 训练场景、会话、消息、评分模型。"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TrainingScenario(Base):
    """训练场景定义。"""

    __tablename__ = "training_scenarios"

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="场景标题",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="场景描述",
    )
    difficulty: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="medium",
        server_default="medium",
        comment="难度: easy / medium / hard",
    )
    customer_persona: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        comment="客户人设 JSON: name, age, personality, mood, background, insurance_knowledge, key_objections",
    )
    product_focus: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="聚焦产品类型",
    )
    sales_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        comment="销售阶段",
    )
    evaluation_criteria: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        comment="评估标准 JSON",
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=10,
        server_default="10",
        comment="建议时长（分钟）",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        comment="是否启用",
    )

    # 关系
    sessions: Mapped[list["TrainingSession"]] = relationship(
        "TrainingSession",
        back_populates="scenario",
        lazy="selectin",
    )


class TrainingSession(Base):
    """训练会话。"""

    __tablename__ = "training_sessions"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    scenario_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_scenarios.id", ondelete="SET NULL"),
        nullable=True,
        comment="场景ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        comment="状态: active / completed / abandoned",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="开始时间",
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="完成时间",
    )
    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        comment="消息数量",
    )

    # 关系
    scenario: Mapped["TrainingScenario"] = relationship(
        "TrainingScenario",
        back_populates="sessions",
    )
    messages: Mapped[list["TrainingMessage"]] = relationship(
        "TrainingMessage",
        back_populates="session",
        lazy="selectin",
        order_by="TrainingMessage.created_at",
    )
    score: Mapped["TrainingScore | None"] = relationship(
        "TrainingScore",
        back_populates="session",
        uselist=False,
        lazy="selectin",
    )


class TrainingMessage(Base):
    """训练消息。"""

    __tablename__ = "training_messages"

    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="会话ID",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="角色: agent / customer / coach",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容",
    )
    score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="评分（coach消息专用）",
    )
    coaching_hint: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        comment="辅导提示 JSON",
    )

    # 关系
    session: Mapped["TrainingSession"] = relationship(
        "TrainingSession",
        back_populates="messages",
    )


class TrainingScore(Base):
    """训练评分。"""

    __tablename__ = "training_scores"

    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="会话ID",
    )
    total_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="总分 (0-100)",
    )
    product_accuracy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="产品准确性 (0-100)",
    )
    empathy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="客户共情 (0-100)",
    )
    closing_action: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="促单动作 (0-100)",
    )
    strengths: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        comment="优势列表",
    )
    weaknesses: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        comment="不足列表",
    )
    recommendations: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        comment="改进建议",
    )

    # 关系
    session: Mapped["TrainingSession"] = relationship(
        "TrainingSession",
        back_populates="score",
    )
