"""Training Service Production 路径测试。

在 DEMO_MODE=false 下直接驱动 TrainingService，使用 SQLite 内存库
(Base.metadata.create_all) 验证生产路径：
- 场景查询（Repository → DB）
- 会话创建 / 查询 / 列表 / 历史
- 消息持久化（agent / customer / coach）
- 评分持久化 + 会话完成
- 统计聚合
- 权限隔离（Agent A 只能访问自己的数据）
- 资源不存在 / 非法状态
- 事务回滚

说明: 当前环境无真实 PostgreSQL，本测试使用项目已有 SQLite 测试能力完成
尽可能接近 Production 的验证；真实 PostgreSQL + pgvector 验收属于后续任务。
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ---- SQLite 兼容：为 JSONB / Vector 注册 SQLite 编译器 ----
# 模型使用 PG 原生类型 (JSONB / pgvector Vector)，SQLite 测试库建表时无法直接
# 编译，这里注册编译器使其渲染为 JSON / BLOB，仅影响测试建表。
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
from app.models import Base, TrainingMessage, TrainingScenario, TrainingScore, TrainingSession, User
from app.services.training_service import TrainingService, seed_training_scenarios

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
    """创建一个最小用户行（SQLite 默认不强制外键）。"""
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


async def _make_production_service(session: AsyncSession, monkeypatch) -> TrainingService:
    """构造生产模式（DEMO_MODE=false）下的 TrainingService。"""
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    return TrainingService(session=session)


async def _seed_one_scenario(session: AsyncSession) -> uuid.UUID:
    """种入一个场景，返回其 id。"""
    created = await seed_training_scenarios(session)
    assert created > 0
    await session.commit()
    scenario = (await session.execute(
        select(TrainingScenario).limit(1)
    )).scalars().first()
    return scenario.id


# ------------------------------------------------------------------
# Scenarios
# ------------------------------------------------------------------

class TestScenariosProduction:
    async def test_seed_scenarios_idempotent(self, session, monkeypatch):
        created_1 = await seed_training_scenarios(session)
        assert created_1 > 0
        await session.commit()
        created_2 = await seed_training_scenarios(session)
        assert created_2 == 0

    async def test_get_scenarios_from_db(self, session, monkeypatch):
        await _seed_one_scenario(session)
        service = await _make_production_service(session, monkeypatch)
        scenarios = await service.get_scenarios()
        assert isinstance(scenarios, list) and len(scenarios) > 0
        first = scenarios[0]
        assert first["id"] and first["title"] and first["difficulty"]

    async def test_get_scenario_detail(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        service = await _make_production_service(session, monkeypatch)
        detail = await service.get_scenario(str(sid))
        assert detail is not None
        assert "evaluation_criteria" in detail
        assert "customer_persona" in detail

    async def test_get_scenario_not_found(self, session, monkeypatch):
        await _seed_one_scenario(session)
        service = await _make_production_service(session, monkeypatch)
        assert await service.get_scenario(str(uuid.uuid4())) is None
        assert await service.get_scenario("not-a-uuid") is None


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

class TestSessionProduction:
    async def test_start_session_persists(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        uid = await _create_user(session, "13900000001")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        detail = await service.start_session(user_id=str(uid), scenario_id=str(sid))
        assert detail["status"] == "active"
        assert detail["message_count"] == 0
        assert detail["scenario_id"] == str(sid)

        # 数据库确实持久化了一条会话
        rows = (await session.execute(
            select(TrainingSession)
        )).scalars().all()
        assert len(rows) == 1
        assert str(rows[0].user_id) == str(uid)

    async def test_start_session_invalid_scenario(self, session, monkeypatch):
        uid = await _create_user(session, "13900000002")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        with pytest.raises(ValueError):
            await service.start_session(user_id=str(uid), scenario_id=str(uuid.uuid4()))

    async def test_get_session_and_list(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        uid = await _create_user(session, "13900000003")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        detail = await service.start_session(user_id=str(uid), scenario_id=str(sid))
        sid_str = detail["id"]

        fetched = await service.get_session(session_id=sid_str, user_id=str(uid))
        assert fetched is not None
        assert fetched["messages"] == []

        listed = await service.list_sessions(user_id=str(uid))
        assert len(listed) == 1
        assert listed[0]["id"] == sid_str

    async def test_get_session_not_found(self, session, monkeypatch):
        await _seed_one_scenario(session)
        uid = await _create_user(session, "13900000004")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        assert await service.get_session(session_id=str(uuid.uuid4()), user_id=str(uid)) is None
        assert await service.get_session(session_id="bad", user_id=str(uid)) is None


# ------------------------------------------------------------------
# Messages
# ------------------------------------------------------------------

class TestMessageProduction:
    async def test_send_message_persists(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        uid = await _create_user(session, "13900000005")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        detail = await service.start_session(user_id=str(uid), scenario_id=str(sid))
        sid_str = detail["id"]

        events = [
            e async for e in service.send_message(
                session_id=sid_str, user_id=str(uid), content="您好，我是您的保险顾问"
            )
        ]
        assert any("turn_complete" in e for e in events)

        # 数据库持久化了 agent/customer/coach 三条消息
        rows = (await session.execute(
            select(TrainingMessage).order_by(TrainingMessage.created_at)
        )).scalars().all()
        assert [r.role for r in rows] == ["agent", "customer", "coach"]

        # 会话详情包含消息且计数正确
        fetched = await service.get_session(session_id=sid_str, user_id=str(uid))
        assert len(fetched["messages"]) == 3
        assert fetched["message_count"] == 2

    async def test_send_message_permission_denied(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        owner = await _create_user(session, "13900000006")
        intruder = await _create_user(session, "13900000007")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        detail = await service.start_session(user_id=str(owner), scenario_id=str(sid))
        sid_str = detail["id"]

        events = [
            e async for e in service.send_message(
                session_id=sid_str, user_id=str(intruder), content="越权尝试"
            )
        ]
        assert any("error" in e for e in events)

    async def test_send_message_completed_session_rejected(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        uid = await _create_user(session, "13900000008")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        detail = await service.start_session(user_id=str(uid), scenario_id=str(sid))
        sid_str = detail["id"]

        # 先完成会话
        events = [
            e async for e in service.complete_session(session_id=sid_str, user_id=str(uid))
        ]
        assert any("scoring_complete" in e for e in events)

        # 已结束会话再发消息被拒绝
        events2 = [
            e async for e in service.send_message(
                session_id=sid_str, user_id=str(uid), content="还能说话吗"
            )
        ]
        assert any("error" in e for e in events2)


# ------------------------------------------------------------------
# Scores & completion
# ------------------------------------------------------------------

class TestScoreProduction:
    async def test_complete_session_persists_score(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        uid = await _create_user(session, "13900000009")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        detail = await service.start_session(user_id=str(uid), scenario_id=str(sid))
        sid_str = detail["id"]
        _ = [
            e async for e in service.send_message(
                session_id=sid_str, user_id=str(uid), content="向您推荐重疾险"
            )
        ]

        events = [
            e async for e in service.complete_session(session_id=sid_str, user_id=str(uid))
        ]
        assert any("score_data" in e for e in events)
        assert any("scoring_complete" in e for e in events)

        # 评分已持久化
        score_row = (await session.execute(
            select(TrainingScore)
        )).scalars().first()
        assert score_row is not None
        assert score_row.total_score >= 0
        assert score_row.session_id == uuid.UUID(sid_str)

        # 会话已标记完成
        tsession = (await session.execute(
            select(TrainingSession)
        )).scalars().first()
        assert tsession.status == "completed"
        assert tsession.completed_at is not None

    async def test_complete_session_permission_denied(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        owner = await _create_user(session, "13900000010")
        intruder = await _create_user(session, "13900000011")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        detail = await service.start_session(user_id=str(owner), scenario_id=str(sid))
        sid_str = detail["id"]

        events = [
            e async for e in service.complete_session(
                session_id=sid_str, user_id=str(intruder)
            )
        ]
        assert any("error" in e for e in events)

    async def test_complete_session_not_found(self, session, monkeypatch):
        uid = await _create_user(session, "13900000012")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        events = [
            e async for e in service.complete_session(
                session_id=str(uuid.uuid4()), user_id=str(uid)
            )
        ]
        assert any("error" in e for e in events)


# ------------------------------------------------------------------
# Permission isolation
# ------------------------------------------------------------------

class TestPermissionIsolation:
    async def test_user_cannot_read_others_session(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        alice = await _create_user(session, "13900000013")
        bob = await _create_user(session, "13900000014")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        alice_detail = await service.start_session(user_id=str(alice), scenario_id=str(sid))

        # Bob 读不到 Alice 的会话，也列不到
        assert await service.get_session(alice_detail["id"], user_id=str(bob)) is None
        assert await service.list_sessions(user_id=str(bob)) == []

        # Alice 能读到自己
        assert await service.get_session(alice_detail["id"], user_id=str(alice)) is not None
        assert len(await service.list_sessions(user_id=str(alice))) == 1


# ------------------------------------------------------------------
# Stats
# ------------------------------------------------------------------

class TestStatsProduction:
    async def test_get_stats_aggregates(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        uid = await _create_user(session, "13900000015")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        detail = await service.start_session(user_id=str(uid), scenario_id=str(sid))
        sid_str = detail["id"]
        _ = [
            e async for e in service.send_message(
                session_id=sid_str, user_id=str(uid), content="您好"
            )
        ]
        _ = [
            e async for e in service.complete_session(session_id=sid_str, user_id=str(uid))
        ]

        stats = await service.get_stats(user_id=str(uid))
        assert stats["total_sessions"] == 1
        assert stats["completed_sessions"] == 1
        assert stats["avg_score"] is not None
        assert stats["best_score"] is not None
        assert len(stats["trend"]) == 7
        assert isinstance(stats["difficulty_distribution"], dict)
        assert isinstance(stats["product_focus_distribution"], dict)

    async def test_get_stats_empty(self, session, monkeypatch):
        uid = await _create_user(session, "13900000016")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        stats = await service.get_stats(user_id=str(uid))
        assert stats["total_sessions"] == 0
        assert stats["completed_sessions"] == 0
        assert stats["avg_score"] is None


# ------------------------------------------------------------------
# Transaction rollback
# ------------------------------------------------------------------

class TestTransactionRollback:
    async def test_start_session_rollback_on_commit_failure(self, session, monkeypatch):
        sid = await _seed_one_scenario(session)
        uid = await _create_user(session, "13900000017")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        original_commit = session.commit

        async def _boom():
            raise RuntimeError("simulated db failure")

        monkeypatch.setattr(session, "commit", _boom)
        with pytest.raises(RuntimeError):
            await service.start_session(user_id=str(uid), scenario_id=str(sid))
        monkeypatch.setattr(session, "commit", original_commit)

        # 回滚后数据库无残留会话
        rows = (await session.execute(
            select(TrainingSession)
        )).scalars().all()
        assert rows == []
