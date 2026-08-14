"""通知、成长、审计仓储层。"""
import uuid

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPreference
from app.models.growth import UserAchievement
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, Message
from app.repositories.base import BaseRepository


# ---- 通知 ----

class NotificationRepository(BaseRepository[Notification]):
    """通知仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Notification, session)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        type_filter: str | None = None,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        """用户通知列表。"""
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_deleted == False,
        )
        count_q = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.is_deleted == False,
        )
        if type_filter:
            query = query.where(Notification.type == type_filter)
            count_q = count_q.where(Notification.type == type_filter)
        if unread_only:
            query = query.where(Notification.is_read == False)
            count_q = count_q.where(Notification.is_read == False)

        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.order_by(Notification.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total

    async def mark_read(self, user_id: uuid.UUID, notification_ids: list[uuid.UUID] | None = None) -> int:
        """批量标记已读。如果 notification_ids 为空则标记全部。返回影响行数。"""
        if notification_ids:
            result = await self.session.execute(
                update(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.id.in_(notification_ids),
                    Notification.is_read == False,
                )
                .values(is_read=True)
            )
        else:
            result = await self.session.execute(
                update(Notification)
                .where(Notification.user_id == user_id, Notification.is_read == False)
                .values(is_read=True)
            )
        await self.session.flush()
        return result.rowcount

    async def unread_count(self, user_id: uuid.UUID) -> int:
        """未读数量。"""
        result = await self.session.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_deleted == False,
            )
        )
        return result.scalar() or 0


class NotificationPreferenceRepository(BaseRepository[NotificationPreference]):
    """通知偏好仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(NotificationPreference, session)

    async def get_by_user(self, user_id: uuid.UUID) -> NotificationPreference | None:
        result = await self.session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: uuid.UUID, **kwargs) -> NotificationPreference:
        """获取或创建用户偏好，然后更新。"""
        existing = await self.get_by_user(user_id)
        if not existing:
            existing = await self.create(user_id=user_id, **kwargs)
        else:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            await self.session.flush()
        return existing


# ---- 成长 ----

class UserAchievementRepository(BaseRepository[UserAchievement]):
    """用户成就仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(UserAchievement, session)

    async def list_by_user(self, user_id: uuid.UUID) -> list[UserAchievement]:
        """用户所有成就。"""
        result = await self.session.execute(
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id, UserAchievement.is_deleted == False)
            .order_by(UserAchievement.created_at.desc())
        )
        return list(result.scalars().all())

    async def unlock(self, user_id: uuid.UUID, code: str, name: str, **kwargs) -> UserAchievement:
        """解锁成就。"""
        result = await self.session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_code == code,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_unlocked = True
            await self.session.flush()
            return existing
        return await self.create(
            user_id=user_id,
            achievement_code=code,
            achievement_name=name,
            is_unlocked=True,
            **kwargs,
        )


# ---- 审计 ----

class AuditLogRepository(BaseRepository[AuditLog]):
    """审计日志仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def list_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
        resource_type: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[AuditLog], int]:
        """审计日志列表。"""
        query = select(AuditLog).where(AuditLog.is_deleted == False)
        count_q = select(func.count()).select_from(AuditLog).where(AuditLog.is_deleted == False)

        if action:
            query = query.where(AuditLog.action == action)
            count_q = count_q.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            count_q = count_q.where(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
            count_q = count_q.where(AuditLog.user_id == user_id)

        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total


# ---- 对话 ----

class ConversationRepository(BaseRepository[Conversation]):
    """对话仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def list_by_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Conversation], int]:
        """用户对话列表。"""
        query = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.is_deleted == False,
        )
        count_q = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.is_deleted == False,
        )
        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.order_by(Conversation.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total


class MessageRepository(BaseRepository[Message]):
    """消息仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def list_by_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        """获取对话的所有消息。"""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())
