"""AI 对话与消息模型。"""

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Conversation(Base):
    """AI 对话会话。"""

    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=True,
        comment="对话标题",
    )
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="product_qa",
        comment="对话类型: product_qa / script_assist / customer_analysis / general",
    )
    customer_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联客户ID",
    )
    context: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        comment="对话上下文",
    )
    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        comment="消息数量",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        comment="状态: active / archived / deleted",
    )

    # 关系
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        lazy="selectin",
        order_by="Message.created_at",
    )


class Message(Base):
    """对话消息。"""

    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="对话ID",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="发送者: user / assistant / system",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容",
    )
    content_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        server_default="text",
        comment="内容类型: text / markdown / json",
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Token 数量",
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="使用的 AI 模型",
    )
    knowledge_sources: Mapped[dict] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        comment="RAG 检索来源",
    )
    compliance_check: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        comment="合规检查结果",
    )
    feedback: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="用户反馈: helpful / unhelpful",
    )

    # 关系
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
