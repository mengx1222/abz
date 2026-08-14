"""Dashboard Service Production 路径测试。

在 DEMO_MODE=false 下直接驱动 DashboardService，使用 SQLite 内存库
(Base.metadata.create_all) 验证生产聚合：
- 空库时返回合法结构（零值）
- 今日统计聚合（互动/成交/待跟进/AI次数）
- AI 建议从真实数据推导
- 最近活动合并（互动/陪练/话术/问答）
- 用户隔离（只看自己负责的客户与自己的活动）

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
    Conversation,
    Customer,
    CustomerFollowup,
    CustomerInteraction,
    Notification,
    Script,
    TrainingSession,
    User,
)
from app.services.dashboard_service import DashboardService

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
    c = Customer(
        name=name,
        assigned_to=user_id,
        organization_id=uuid.uuid4(),
        current_stage=stage,
        intention_level=intent,
    )
    session.add(c)
    await session.flush()
    return c.id


async def _add_interaction(session, customer_id, *, content="通话记录"):
    i = CustomerInteraction(customer_id=customer_id, type="phone", content=content)
    session.add(i)
    await session.flush()


async def _add_followup(session, customer_id, *, status="pending"):
    f = CustomerFollowup(customer_id=customer_id, scheduled_date=datetime.now(timezone.utc), status=status)
    session.add(f)
    await session.flush()


async def _make_production_service(session: AsyncSession, monkeypatch) -> DashboardService:
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    return DashboardService(session=session)


class TestDashboardProduction:
    async def test_empty_db_returns_valid_structure(self, session, monkeypatch):
        uid = await _create_user(session, "13900330001")
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        ov = await service.get_overview(uid, "测试用户")
        assert ov.user_name == "测试用户"
        assert ov.greeting
        assert len(ov.today_stats) == 4
        assert ov.today_stats[0].value == "0"
        assert ov.ai_suggestions == []
        assert ov.recent_activities == []
        assert ov.unread_notifications == 0
        assert len(ov.quick_actions) == 4

    async def test_today_stats_aggregate(self, session, monkeypatch):
        uid = await _create_user(session, "13900330002")
        cid = await _add_customer(session, uid, name="王丽华", stage="closed_won", intent=5)
        await _add_interaction(session, cid, content="今天通话")
        await _add_followup(session, cid, status="pending")
        # 一条不属于该用户的客户，不应计入
        other = await _create_user(session, "13900330003")
        other_cid = await _add_customer(session, other, name="别人")
        await _add_interaction(session, other_cid, content="别的客户")
        # AI 日志 + 未读通知
        session.add(AIRequestLog(user_id=uid, module="product_qa", provider="mock", request_type="chat"))
        session.add(Notification(user_id=uid, type="system", title="通知", content="内容", is_read=False))
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        ov = await service.get_overview(uid, "测试")
        stat_map = {s.label: s for s in ov.today_stats}
        assert stat_map["今日互动"].value == "1"  # 只计自己的客户
        assert stat_map["成交保单"].value == "1"
        assert stat_map["待跟进客户"].value == "1"
        assert stat_map["AI 问答次数"].value == "1"
        assert ov.unread_notifications == 1

    async def test_suggestions_derived_from_data(self, session, monkeypatch):
        uid = await _create_user(session, "13900330004")
        cid = await _add_customer(session, uid, name="高意向", stage="proposal", intent=5)
        await _add_followup(session, cid, status="pending")
        session.add(Notification(user_id=uid, type="system", title="n", content="c", is_read=False))
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        ov = await service.get_overview(uid, "测试")
        tags = {s.tag for s in ov.ai_suggestions}
        assert "紧急跟进" in tags
        assert "高意向" in tags
        assert "通知" in tags

    async def test_recent_activities_merged(self, session, monkeypatch):
        uid = await _create_user(session, "13900330005")
        cid = await _add_customer(session, uid, name="李女士")
        await _add_interaction(session, cid, content="跟进续保")
        session.add(Script(title="续保话术", style="affinity", content="内容", created_by=uid))
        session.add(TrainingSession(user_id=uid, status="completed", completed_at=datetime.now(timezone.utc)))
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        ov = await service.get_overview(uid, "测试")
        titles = [a.title for a in ov.recent_activities]
        assert any("互动" in t for t in titles)
        assert "AI话术生成" in titles
        assert "完成AI陪练" in titles

    async def test_user_isolation(self, session, monkeypatch):
        alice = await _create_user(session, "13900330006")
        bob = await _create_user(session, "13900330007")
        alice_cid = await _add_customer(session, alice, name="Alice客户")
        await _add_interaction(session, alice_cid, content="Alice互动")
        session.add(Notification(user_id=alice, type="system", title="a", content="c", is_read=False))
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        alice_ov = await service.get_overview(alice, "Alice")
        bob_ov = await service.get_overview(bob, "Bob")

        alice_stats = {s.label: s for s in alice_ov.today_stats}
        bob_stats = {s.label: s for s in bob_ov.today_stats}
        assert alice_stats["今日互动"].value == "1"
        assert bob_stats["今日互动"].value == "0"
        assert alice_ov.unread_notifications == 1
        assert bob_ov.unread_notifications == 0
        assert len(alice_ov.recent_activities) >= 1
        assert bob_ov.recent_activities == []
