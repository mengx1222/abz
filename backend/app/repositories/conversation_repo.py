"""Conversation/Message 仓储 —— 生产会话历史持久化（ULTIMATE P0-2）。

提供：归属校验（越权 404 语义）、按用户列表、详情消息、会话创建、
消息追加（message_count 同步递增）。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message


class ConversationRepository:
    """产品问答会话与消息的数据库访问。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_owned(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation | None:
        """按归属取会话；越权或不存在返回 None（配合 404 语义）。"""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.status == "active",
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def list_by_user(
        self, user_id: uuid.UUID, limit: int = 50
    ) -> list[Conversation]:
        """当前用户的会话列表（按更新时间倒序）。"""
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.status == "active",
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_messages(
        self, conversation_id: uuid.UUID, limit: int = 8
    ) -> list[Message]:
        """最近 limit 条消息，按时间升序返回（用于上下文注入）。"""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        rows.reverse()
        return rows

    async def create_conversation(
        self,
        user_id: uuid.UUID,
        title: str,
        conversation_type: str = "product_qa",
    ) -> Conversation:
        """创建新会话（标题截断到 500 字）。"""
        conv = Conversation(
            user_id=user_id,
            title=(title or "")[:500],
            type=conversation_type,
            message_count=0,
        )
        self.db.add(conv)
        await self.db.flush()
        return conv

    async def append_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        *,
        content_type: str = "text",
        model: str | None = None,
        token_count: int | None = None,
        knowledge_sources: list | None = None,
        finish_reason: str | None = None,
    ) -> Message:
        """追加消息并同步递增会话 message_count。"""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            content_type=content_type,
            model=model,
            token_count=token_count,
            knowledge_sources=knowledge_sources or [],
            finish_reason=finish_reason,
        )
        self.db.add(msg)
        conv = await self.db.get(Conversation, conversation_id)
        if conv is not None:
            conv.message_count = (conv.message_count or 0) + 1
            conv.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return msg
