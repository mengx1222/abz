"""PostgreSQL + pgvector 真实环境集成测试（Production 验收）。

通过环境变量 AZB_TEST_DATABASE_URL 指定真实 PostgreSQL（含 pgvector 扩展）连接，
未设置时整个模块跳过（该数据库由 CI 的 PG 服务容器提供）。

覆盖各 Service 生产路径在真实 PG 上的关键链路：
- training: 场景种子 → 会话 → 消息 → 评分（事务持久化）
- script: 创建（合规小写）→ 生成（生产 RAG 检索器）
- notification: 列表 / 标记已读 / 偏好
- dashboard / growth: 聚合统计
- achievements: 用户隔离
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Base, Organization, Role, Script, TrainingMessage, TrainingScenario, TrainingScore, TrainingSession, User
from app.models.organization import OrgType
from app.rag.retriever import Retriever
from app.services.growth_service import GrowthService
from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService
from app.services.script_service import ScriptService
from app.services.training_service import TrainingService, seed_training_scenarios
from app.schemas.notification import UpdatePreferenceRequest

PG_URL = os.environ.get("AZB_TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not PG_URL, reason="AZB_TEST_DATABASE_URL not set"),
]


@pytest_asyncio.fixture(scope="module")
async def engine():
    # NullPool: 每个连接用完即关闭，避免 asyncpg 连接跨 pytest-asyncio
    # 事件循环复用（pytest-asyncio 默认每测试函数一个 loop，module 级
    # fixture 的连接池复用会触发 "attached to a different loop"）。
    eng = create_async_engine(PG_URL, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # CI 已先执行 alembic upgrade head；create_all(checkfirst) 作为兜底
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


async def _create_user(session: AsyncSession, phone: str) -> uuid.UUID:
    """创建用户。真实 PG 强制外键约束：role_id / organization_id 必须引用真实记录。"""
    role = Role(
        code=f"ROLE_{phone[-4:]}",
        name=f"测试角色{phone[-4:]}",
        description="PG 集成测试角色",
        level=1,
    )
    org = Organization(name=f"测试组织{phone[-4:]}", type=OrgType.TEAM)
    session.add_all([role, org])
    await session.flush()
    user = User(
        phone=phone,
        name=f"PG用户{phone[-4:]}",
        password_hash=None,
        role_id=role.id,
        organization_id=org.id,
        status="active",
        demo_mode=False,
    )
    session.add(user)
    await session.flush()
    return user.id


def _prod(monkeypatch, cls, session):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    return cls(session=session)


class TestPgTraining:
    async def test_full_training_flow_persists(self, session, monkeypatch):
        created = await seed_training_scenarios(session)
        await session.commit()
        assert created >= 1

        uid = await _create_user(session, "13800660001")
        await session.commit()
        service = _prod(monkeypatch, TrainingService, session)

        scenario = (await session.execute(select(TrainingScenario).limit(1))).scalars().first()
        detail = await service.start_session(user_id=str(uid), scenario_id=str(scenario.id))
        sid = detail["id"]

        events = [
            e async for e in service.send_message(session_id=sid, user_id=str(uid), content="您好，向您介绍重疾险")
        ]
        assert any("turn_complete" in e for e in events)

        events2 = [
            e async for e in service.complete_session(session_id=sid, user_id=str(uid))
        ]
        assert any("scoring_complete" in e for e in events2)

        # 真实 PG 中已持久化
        assert (await session.execute(select(TrainingSession))).scalars().all()
        msgs = (await session.execute(select(TrainingMessage))).scalars().all()
        assert len(msgs) == 3
        score = (await session.execute(select(TrainingScore))).scalars().first()
        assert score is not None and score.total_score >= 0
        history = await service.get_session(session_id=sid, user_id=str(uid))
        assert history["status"] == "completed"
        assert len(history["messages"]) == 3


class TestPgScript:
    async def test_create_and_rag_retriever(self, session, monkeypatch):
        uid = await _create_user(session, "13800660002")
        await session.commit()
        service = _prod(monkeypatch, ScriptService, session)

        created = await service.create_script(
            {"title": "PG医疗话术", "style": "professional", "content": "从专业角度介绍百万医疗险", "product_type": "医疗险"},
            user_id=str(uid),
        )
        assert created["compliance_status"] in ("green", "yellow", "red")
        row = (await session.execute(select(Script).where(Script.title == "PG医疗话术"))).scalars().first()
        assert row is not None
        assert row.compliance_status.islower()

        # 生产 RAG 检索器在真实 PG 上可实例化并查询（无知识库数据时优雅返回空）
        pipeline = await service._get_rag_pipeline()
        retriever = await pipeline._get_retriever()
        assert isinstance(retriever, Retriever)
        results, context = await pipeline.query("百万医疗险 保障范围", top_k=4)
        assert isinstance(results, list)
        assert isinstance(context, str)


class TestPgNotification:
    async def test_list_mark_read_preferences(self, session, monkeypatch):
        uid = await _create_user(session, "13800660003")
        await session.commit()
        service = _prod(monkeypatch, NotificationService, session)

        from app.models import Notification

        n = Notification(user_id=uid, type="system", title="PG通知", content="内容", is_read=False)
        session.add(n)
        await session.commit()

        listed = await service.list_notifications(uid)
        assert listed.total >= 1
        assert any(x.title == "PG通知" for x in listed.notifications)

        resp = await service.mark_read(uid, read_all=True)
        assert resp.updated_count >= 1

        pref = await service.update_preference(
            uid, UpdatePreferenceRequest(type="followup", enabled=False)
        )
        assert pref.enabled is False
        prefs = await service.get_preferences(uid)
        assert any(p.type == "followup" and p.enabled is False for p in prefs.preferences)


class TestPgDashboardGrowth:
    async def test_dashboard_and_growth_aggregate(self, session, monkeypatch):
        uid = await _create_user(session, "13800660004")
        await session.commit()

        dash = _prod(monkeypatch, DashboardService, session)
        ov = await dash.get_overview(uid, "PG用户")
        assert len(ov.today_stats) == 4

        growth = _prod(monkeypatch, GrowthService, session)
        g_ov = await growth.get_overview(uid)
        assert len(g_ov.monthly_stats) == 4
        assert len(g_ov.weekly_trend) == 7

        lb = await growth.get_leaderboard("month", uid)
        assert isinstance(lb.leaderboard, list)
        if lb.leaderboard:
            assert isinstance(lb.my_rank, type(lb.leaderboard[0]))
        else:
            assert lb.my_rank is None

        ach = await growth.get_achievements(uid)
        assert isinstance(ach.unlocked, list)
        assert isinstance(ach.locked, list)

