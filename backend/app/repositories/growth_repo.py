"""成长体系仓储层：GrowthRepository。

负责成长体系相关的数据库查询与聚合（Production 模式），
包括：概览统计、排行榜聚合、组织范围解析。
"""
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_log import AIRequestLog
from app.models.customer import Customer, CustomerFollowup, CustomerInteraction
from app.models.growth import UserAchievement
from app.models.organization import Organization
from app.models.training import TrainingSession, TrainingScore
from app.models.user import User


class GrowthRepository:
    """成长体系查询仓储（Production 模式使用）。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # 概览统计
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

    async def count_customer_interactions(
        self, customer_ids: list[uuid.UUID], year: int, month: int
    ) -> int:
        """统计指定月份客户互动次数。"""
        if not customer_ids:
            return 0
        return (
            await self.session.execute(
                select(func.count())
                .select_from(CustomerInteraction)
                .where(
                    CustomerInteraction.customer_id.in_(customer_ids),
                    func.extract("year", CustomerInteraction.created_at) == year,
                    func.extract("month", CustomerInteraction.created_at) == month,
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

    async def count_ai_usage(self, user_id: uuid.UUID, year: int, month: int) -> int:
        """AI 使用次数（按年月）。"""
        return (
            await self.session.execute(
                select(func.count()).select_from(AIRequestLog).where(
                    AIRequestLog.user_id == user_id,
                    func.extract("year", AIRequestLog.created_at) == year,
                    func.extract("month", AIRequestLog.created_at) == month,
                )
            )
        ).scalar() or 0

    async def count_interactions_on_day(
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

    async def list_training_scores(self, user_id: uuid.UUID) -> list[TrainingScore]:
        """用户所有陪练评分（排除软删除训练会话）。"""
        result = await self.session.execute(
            select(TrainingScore)
            .join(TrainingSession, TrainingScore.session_id == TrainingSession.id)
            .where(TrainingSession.user_id == user_id, TrainingSession.is_deleted == False)
        )
        return list(result.scalars().all())

    async def count_completed_trainings(self, user_id: uuid.UUID) -> int:
        """完成训练次数。"""
        return (
            await self.session.execute(
                select(func.count()).select_from(TrainingSession).where(
                    TrainingSession.user_id == user_id,
                    TrainingSession.status == "completed",
                    TrainingSession.is_deleted == False,
                )
            )
        ).scalar() or 0

    async def count_unlocked_achievements(self, user_id: uuid.UUID) -> int:
        """已解锁成就数。"""
        return (
            await self.session.execute(
                select(func.count()).select_from(UserAchievement).where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.is_unlocked == True,
                )
            )
        ).scalar() or 0

    # ------------------------------------------------------------------
    # 排行榜
    # ------------------------------------------------------------------

    async def get_leaderboard_rows(
        self, org_ids: list[uuid.UUID] | None = None
    ) -> list[tuple[uuid.UUID, str, str, int]]:
        """按真实活动聚合排行榜数据。

        返回 [(user_id, name, org_name, score)]，按 score 降序。
        org_ids 为 None 表示全部组织；否则仅统计指定组织范围内的用户。
        """
        stmt = (
            select(User.id, User.name, Organization.name)
            .outerjoin(Organization, User.organization_id == Organization.id)
            .where(User.is_deleted == False)
        )
        if org_ids is not None:
            stmt = stmt.where(User.organization_id.in_(org_ids))
        user_rows = list((await self.session.execute(stmt)).all())

        closed_counts = dict(
            (
                await self.session.execute(
                    select(Customer.assigned_to, func.count()).where(
                        Customer.current_stage == "closed_won",
                        Customer.is_deleted == False,
                    ).group_by(Customer.assigned_to)
                )
            ).all()
        )
        ach_counts = dict(
            (
                await self.session.execute(
                    select(UserAchievement.user_id, func.count()).where(
                        UserAchievement.is_unlocked == True,
                    ).group_by(UserAchievement.user_id)
                )
            ).all()
        )
        train_counts = dict(
            (
                await self.session.execute(
                    select(TrainingSession.user_id, func.count()).where(
                        TrainingSession.status == "completed",
                        TrainingSession.is_deleted == False,
                    ).group_by(TrainingSession.user_id)
                )
            ).all()
        )

        scored = []
        for uid, name, org_name in user_rows:
            s = (
                closed_counts.get(uid, 0) * 100
                + ach_counts.get(uid, 0) * 50
                + train_counts.get(uid, 0) * 10
            )
            if s > 0:
                scored.append((uid, name, org_name or "", s))
        scored.sort(key=lambda e: e[3], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # 组织范围
    # ------------------------------------------------------------------

    async def get_child_org_ids(self, org_id: uuid.UUID) -> list[uuid.UUID]:
        """获取指定组织的直接子组织 ID。"""
        result = await self.session.execute(
            select(Organization.id).where(Organization.parent_id == org_id)
        )
        return list(result.scalars().all())

    async def get_org_scope(
        self, user: User, role_level: int
    ) -> list[uuid.UUID] | None:
        """解析排行榜可见组织范围。

        - role_level >= 90（HQ_ADMIN / SYSTEM_ADMIN）：全部组织（None）
        - role_level >= 80（BRANCH_ADMIN）：本组织 + 直接子组织
        - 其他（TEAM_LEADER / AGENT）：仅本组织（优先 team_id）
        """
        if role_level >= 90:
            return None
        if role_level >= 80:
            child_ids = await self.get_child_org_ids(user.organization_id)
            return [user.organization_id] + child_ids
        scope_org_id = user.team_id or user.organization_id
        return [scope_org_id]
