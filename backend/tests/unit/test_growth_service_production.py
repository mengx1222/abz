"""Growth Service Production 路径测试。

在 DEMO_MODE=false 下直接驱动 GrowthService，使用 SQLite 内存库
(Base.metadata.create_all) 验证生产聚合：
- 成长概览（月度统计 / 周趋势 / 能力评分 / 等级）
- 排行榜（按真实活动聚合打分排序 + 我的排名）
- 成就列表（按用户隔离）
- 空库时的合法结构

说明: 当前环境无真实 PostgreSQL，本测试使用项目已有 SQLite 测试能力完成
尽可能接近 Production 的验证；真实 PostgreSQL + pgvector 验收属于后续任务。
"""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ---- SQLite 兼容：为 JSONB / Vector 注册 SQLite 编译器（仅影响测试建表） ----
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_, compiler, **kw):
    return "BLOB"


from app.core.config import settings
from app.models import (
    AIRequestLog,
    Base,
    Customer,
    CustomerInteraction,
    TrainingScore,
    TrainingSession,
    User,
    UserAchievement,
)
from app.services.growth_service import GrowthService

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


async def _create_user(session: AsyncSession, phone: str) -> uuid.UUID:
    user = User(
        phone=phone,
        name=f"用户{phone[-4:]}",
        password_hash=None,
        role_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        status="active",
        demo_mode=False,
    )
    session.add(user)
    await session.flush()
    return user.id


async def _add_customer(session, user_id, *, name="客户", stage="initial_contact", intent=3):
    c = Customer(name=name, assigned_to=user_id, organization_id=uuid.uuid4(), current_stage=stage, intention_level=intent)
    session.add(c)
    await session.flush()
    return c.id


async def _add_training_score(session, user_id):
    ts = TrainingSession(user_id=user_id, status="completed", completed_at=datetime.now(timezone.utc))
    session.add(ts)
    await session.flush()
    score = TrainingScore(
        session_id=ts.id,
        total_score=80, product_accuracy=85, empathy=78, closing_action=70,
        strengths=[], weaknesses=[], recommendations=[],
    )
    session.add(score)
    await session.flush()
    return ts.id


async def _add_achievement(session, user_id, *, name="成就", unlocked=True):
    a = UserAchievement(
        user_id=user_id, achievement_code=name, achievement_name=name,
        description="描述", category="sales", icon="🏅", is_unlocked=unlocked,
    )
    session.add(a)
    await session.flush()


async def _make_production_service(session: AsyncSession, monkeypatch) -> GrowthService:
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    return GrowthService(session=session)


class TestGrowthOverviewProduction:
    async def test_empty_db_structure(self, session, monkeypatch):
        uid = await _create_user(session, "13900440001")
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        ov = await service.get_overview(uid)
        assert len(ov.monthly_stats) == 4
        assert ov.monthly_stats[0].value == "0"
        assert len(ov.weekly_trend) == 7
        assert ov.ability_scores == []
        assert ov.learning_courses == []
        assert ov.level >= 1
        assert ov.total_exp == 0

    async def test_overview_aggregates(self, session, monkeypatch):
        uid = await _create_user(session, "13900440002")
        cid = await _add_customer(session, uid, name="王女士", stage="closed_won", intent=5)
        session.add(CustomerInteraction(customer_id=cid, type="phone", content="本月互动"))
        session.add(AIRequestLog(user_id=uid, module="product_qa", provider="mock", request_type="chat"))
        await _add_training_score(session, uid)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        ov = await service.get_overview(uid)
        stats = {s.label: s for s in ov.monthly_stats}
        assert stats["本月互动"].value == "1"
        assert stats["成交保单"].value == "1"
        assert stats["AI 使用次数"].value == "1"
        # 能力评分来自陪练评分
        ability = {a.label: a.score for a in ov.ability_scores}
        assert ability["产品知识"] == 85
        assert ability["综合表现"] == 80
        # 等级/经验来自活动
        assert ov.total_exp >= 10  # 至少 1 次完成陪练
        assert ov.level >= 1


class TestGrowthLeaderboardProduction:
    async def test_leaderboard_ranks_by_activity(self, session, monkeypatch):
        alice = await _create_user(session, "13900440003")
        bob = await _create_user(session, "13900440004")
        # Alice: 1 closed_won + 1 成就 = 150 分
        await _add_customer(session, alice, name="A", stage="closed_won")
        await _add_achievement(session, alice, name="成交先锋")
        # Bob: 1 次陪练 = 10 分
        await _add_training_score(session, bob)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        resp = await service.get_leaderboard("month", alice)
        assert len(resp.leaderboard) == 2
        assert resp.leaderboard[0].user_name.startswith("用户")
        assert resp.leaderboard[0].score > resp.leaderboard[1].score
        assert resp.my_rank is not None
        assert resp.my_rank.rank == 1

    async def test_leaderboard_empty(self, session, monkeypatch):
        uid = await _create_user(session, "13900440005")
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        resp = await service.get_leaderboard("month", uid)
        assert resp.leaderboard == []
        assert resp.my_rank is None


class TestGrowthAchievementsProduction:
    async def test_achievements_scoped_to_user(self, session, monkeypatch):
        alice = await _create_user(session, "13900440006")
        bob = await _create_user(session, "13900440007")
        await _add_achievement(session, alice, name="已解锁成就", unlocked=True)
        await _add_achievement(session, alice, name="未解锁成就", unlocked=False)
        await _add_achievement(session, bob, name="Bob成就", unlocked=True)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        alice_list = await service.get_achievements(alice)
        assert len(alice_list.unlocked) == 1
        assert len(alice_list.locked) == 1
        assert alice_list.unlocked[0].name == "已解锁成就"

        bob_list = await service.get_achievements(bob)
        assert len(bob_list.unlocked) == 1
        assert bob_list.unlocked[0].name == "Bob成就"
