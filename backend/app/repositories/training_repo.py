"""训练仓储层。"""
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import (
    TrainingScenario, TrainingSession, TrainingMessage, TrainingScore,
)
from app.repositories.base import BaseRepository


class TrainingScenarioRepository(BaseRepository[TrainingScenario]):
    """训练场景仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(TrainingScenario, session)

    async def list_active(
        self,
        page: int = 1,
        page_size: int = 20,
        difficulty: str | None = None,
        category: str | None = None,
    ) -> tuple[list[TrainingScenario], int]:
        """列出活跃场景。"""
        query = select(TrainingScenario).where(
            TrainingScenario.is_deleted == False,
            TrainingScenario.is_active == True,
        )
        count_q = select(func.count()).select_from(TrainingScenario).where(
            TrainingScenario.is_deleted == False,
            TrainingScenario.is_active == True,
        )
        if difficulty:
            query = query.where(TrainingScenario.difficulty == difficulty)
            count_q = count_q.where(TrainingScenario.difficulty == difficulty)
        if category:
            query = query.where(TrainingScenario.product_focus == category)
            count_q = count_q.where(TrainingScenario.product_focus == category)

        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.order_by(TrainingScenario.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total


class TrainingSessionRepository(BaseRepository[TrainingSession]):
    """训练会话仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(TrainingSession, session)

    async def list_by_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[TrainingSession], int]:
        """用户训练历史。"""
        query = select(TrainingSession).where(
            TrainingSession.user_id == user_id,
            TrainingSession.is_deleted == False,
        )
        count_q = select(func.count()).select_from(TrainingSession).where(
            TrainingSession.user_id == user_id,
            TrainingSession.is_deleted == False,
        )
        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.order_by(TrainingSession.started_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total


class TrainingMessageRepository(BaseRepository[TrainingMessage]):
    """训练消息仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(TrainingMessage, session)

    async def list_by_session(self, session_id: uuid.UUID) -> list[TrainingMessage]:
        """获取会话的所有消息。"""
        result = await self.session.execute(
            select(TrainingMessage)
            .where(TrainingMessage.session_id == session_id)
            .order_by(TrainingMessage.created_at.asc())
        )
        return list(result.scalars().all())


class TrainingScoreRepository(BaseRepository[TrainingScore]):
    """训练评分仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(TrainingScore, session)

    async def get_by_session(self, session_id: uuid.UUID) -> TrainingScore | None:
        """获取会话的评分。"""
        result = await self.session.execute(
            select(TrainingScore).where(TrainingScore.session_id == session_id)
        )
        return result.scalar_one_or_none()
