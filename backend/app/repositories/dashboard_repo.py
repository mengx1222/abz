"""Dashboard 仓储层：DashboardRepository。

负责 Dashboard 概览相关的数据库查询与聚合（Production 模式）。
"""
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_log import AIRequestLog
from app.models.conversation import Conversation
from app.models.customer import Customer, CustomerFollowup, CustomerInteraction
from app.models.notification import Notification
from app.models.script import Script
from app.models.training import TrainingSession


class DashboardRepository:
    """Dashboard 查询仓储（Production 模式使用）。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # 今日统计
    # ------------------------------------------------------------------

    async def list_customer_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """当前用户负责的客户 ID 列表（排除软删除）。"""
        result = await self.session.execute(
            select(Customer.id).where(
                Customer.assigned_to == user_id,
                Customer.is_deleted == False,
            )
        )
        return list(result.scalars().all())

    async def count_interactions_on(
        self, customer_ids: list[uuid.UUID], day: date
    ) -> int:
        """指定日期客户互动次数。"""
        if not customer_ids:
            return 0
        return (
            await self.session.execute(
                select(func.count()).select_from(CustomerInteraction).where(
                    CustomerInteraction.customer_id.in_(customer_ids),
                    func.date(CustomerInteraction.created_at) == day,
                )
            )
        ).scalar() or 0

    async def count_closed_won(self, customer_ids: list[uuid.UUID]) -> int:
        """成交客户数。"""
        if not customer_ids:
            return 0
        return (
            await self.session.execute(
                select(func.count()).select_from(Customer).where(
                    Customer.id.in_(customer_ids),
                    Customer.current_stage == "closed_won",
                )
            )
        ).scalar() or 0

    async def count_high_intent(self, customer_ids: list[uuid.UUID]) -> int:
        """高意向客户数（意向度 >= 4）。"""
        if not customer_ids:
            return 0
        return (
            await self.session.execute(
                select(func.count()).select_from(Customer).where(
                    Customer.id.in_(customer_ids),
                    Customer.intention_level >= 4,
                )
            )
        ).scalar() or 0

    async def count_pending_followups(self, customer_ids: list[uuid.UUID]) -> int:
        """待跟进客户数。"""
        if not customer_ids:
            return 0
        return (
            await self.session.execute(
                select(func.count()).select_from(CustomerFollowup).where(
                    CustomerFollowup.customer_id.in_(customer_ids),
                    CustomerFollowup.status == "pending",
                )
            )
        ).scalar() or 0

    async def count_ai_usage_on(self, user_id: uuid.UUID, day: date) -> int:
        """指定日期 AI 使用次数。"""
        return (
            await self.session.execute(
                select(func.count()).select_from(AIRequestLog).where(
                    AIRequestLog.user_id == user_id,
                    func.date(AIRequestLog.created_at) == day,
                )
            )
        ).scalar() or 0

    async def count_unread_notifications(self, user_id: uuid.UUID) -> int:
        """未读通知数。"""
        return (
            await self.session.execute(
                select(func.count()).select_from(Notification).where(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.is_deleted == False,
                )
            )
        ).scalar() or 0

    # ------------------------------------------------------------------
    # 最近活动
    # ------------------------------------------------------------------

    async def get_recent_completed_training(
        self, user_id: uuid.UUID
    ) -> TrainingSession | None:
        """最近一次完成的陪练会话。"""
        result = await self.session.execute(
            select(TrainingSession).where(
                TrainingSession.user_id == user_id,
                TrainingSession.status == "completed",
            ).order_by(TrainingSession.completed_at.desc()).limit(1)
        )
        return result.scalars().first()

    async def list_recent_interactions(
        self, customer_ids: list[uuid.UUID], limit: int = 5
    ) -> list[tuple[CustomerInteraction, Customer]]:
        """最近互动（含客户信息）。"""
        if not customer_ids:
            return []
        result = await self.session.execute(
            select(CustomerInteraction, Customer)
            .join(Customer, CustomerInteraction.customer_id == Customer.id)
            .where(CustomerInteraction.customer_id.in_(customer_ids))
            .order_by(CustomerInteraction.created_at.desc())
            .limit(limit)
        )
        return list(result.all())

    async def list_recent_trainings(
        self, user_id: uuid.UUID, limit: int = 3
    ) -> list[TrainingSession]:
        """最近完成的陪练会话。"""
        result = await self.session.execute(
            select(TrainingSession).where(
                TrainingSession.user_id == user_id,
                TrainingSession.status == "completed",
            ).order_by(TrainingSession.completed_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent_scripts(
        self, user_id: uuid.UUID, limit: int = 3
    ) -> list[Script]:
        """最近生成的话术。"""
        result = await self.session.execute(
            select(Script).where(Script.created_by == user_id)
            .order_by(Script.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent_conversations(
        self, user_id: uuid.UUID, limit: int = 3
    ) -> list[Conversation]:
        """最近的产品问答会话。"""
        result = await self.session.execute(
            select(Conversation).where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
