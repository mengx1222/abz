"""AI请求日志模型 —— 记录所有AI调用的追踪信息。"""
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AIRequestLog(Base):
    """AI请求日志 —— 可观测性核心表。"""

    __tablename__ = "ai_request_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="发起请求的用户"
    )
    module: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="模块：product_qa/script_gen/training等"
    )
    provider: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="AI Provider: mock/deepseek/qwen/openai"
    )
    model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="", comment="使用的模型名称"
    )
    request_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="请求类型：chat/embed/rerank"
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="Prompt Token数"
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="Completion Token数"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="延迟(ms)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success", comment="状态：success/error/timeout"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    request_params: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="请求参数（脱敏后）"
    )
    response_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="响应摘要"
    )

    def __repr__(self) -> str:
        return f"<AIRequestLog id={self.id} module={self.module!r} status={self.status!r}>"


class AIFeedback(Base):
    """AI反馈 —— 用户对AI回答的反馈。"""

    __tablename__ = "ai_feedbacks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True, comment="反馈用户"
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="关联会话"
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="关联消息"
    )
    rating: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="评分：up/down"
    )
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="文字反馈"
    )

    def __repr__(self) -> str:
        return f"<AIFeedback id={self.id} rating={self.rating!r}>"
