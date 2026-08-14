"""Notification Service Production 路径测试。

在 DEMO_MODE=false 下直接驱动 NotificationService，使用 SQLite 内存库
(Base.metadata.create_all) 验证生产路径：
- 通知列表（按用户隔离 + 类型筛选 + 未读数）
- 标记已读（按 ID / 全部）
- 偏好读取（默认 / 数据库行）
- 偏好更新（创建行 / 更新布尔列 / 未知类型）
- 权限隔离（用户间互不影响）
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
from app.models import Base, Notification, NotificationPreference, User
from app.services.notification_service import NotificationService
from app.schemas.notification import UpdatePreferenceRequest

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


async def _add_notification(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    type_: str = "system",
    title: str = "通知",
    content: str = "内容",
    read: bool = False,
) -> Notification:
    n = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        content=content,
        is_read=read,
        action_url="/test",
        metadata_={"k": "v"},
    )
    session.add(n)
    await session.flush()
    return n


async def _make_production_service(session: AsyncSession, monkeypatch) -> NotificationService:
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    return NotificationService(session=session)


# ------------------------------------------------------------------
# List
# ------------------------------------------------------------------

class TestListNotificationsProduction:
    async def test_list_scoped_to_user(self, session, monkeypatch):
        alice = await _create_user(session, "13900220001")
        bob = await _create_user(session, "13900220002")
        await _add_notification(session, alice, type_="system", title="Alice通知")
        await _add_notification(session, bob, type_="followup", title="Bob通知")
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        alice_resp = await service.list_notifications(alice)
        assert alice_resp.total == 1
        assert alice_resp.notifications[0].title == "Alice通知"
        bob_resp = await service.list_notifications(bob)
        assert bob_resp.total == 1
        assert bob_resp.notifications[0].title == "Bob通知"

    async def test_list_type_filter_and_unread(self, session, monkeypatch):
        uid = await _create_user(session, "13900220003")
        await _add_notification(session, uid, type_="system", title="系统1", read=False)
        await _add_notification(session, uid, type_="system", title="系统2", read=True)
        await _add_notification(session, uid, type_="training", title="训练1", read=False)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        all_resp = await service.list_notifications(uid)
        assert all_resp.total == 3
        assert all_resp.unread_count == 2

        sys_resp = await service.list_notifications(uid, type_filter="system")
        assert sys_resp.total == 2

    async def test_list_pagination(self, session, monkeypatch):
        uid = await _create_user(session, "13900220004")
        for i in range(5):
            await _add_notification(session, uid, type_="system", title=f"N{i}", read=False)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        page1 = await service.list_notifications(uid, page=1, page_size=2)
        assert len(page1.notifications) == 2
        assert page1.total == 5
        page3 = await service.list_notifications(uid, page=3, page_size=2)
        assert len(page3.notifications) == 1


# ------------------------------------------------------------------
# Mark read
# ------------------------------------------------------------------

class TestMarkReadProduction:
    async def test_mark_read_specific(self, session, monkeypatch):
        uid = await _create_user(session, "13900220005")
        n1 = await _add_notification(session, uid, type_="system", title="N1", read=False)
        n2 = await _add_notification(session, uid, type_="system", title="N2", read=False)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        resp = await service.mark_read(uid, notification_ids=[str(n1.id)])
        assert resp.updated_count == 1

        rows = (await session.execute(select(Notification).order_by(Notification.title))).scalars().all()
        read_map = {r.title: r.is_read for r in rows}
        assert read_map == {"N1": True, "N2": False}

    async def test_mark_read_all(self, session, monkeypatch):
        uid = await _create_user(session, "13900220006")
        await _add_notification(session, uid, type_="system", title="N1", read=False)
        await _add_notification(session, uid, type_="system", title="N2", read=True)
        await _add_notification(session, uid, type_="system", title="N3", read=False)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        resp = await service.mark_read(uid, read_all=True)
        assert resp.updated_count == 2

    async def test_mark_read_scoped_to_user(self, session, monkeypatch):
        alice = await _create_user(session, "13900220007")
        bob = await _create_user(session, "13900220008")
        await _add_notification(session, alice, type_="system", title="A", read=False)
        await _add_notification(session, bob, type_="system", title="B", read=False)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        # Bob 标记全部只影响 Bob
        resp = await service.mark_read(bob, read_all=True)
        assert resp.updated_count == 1

        rows = (await session.execute(select(Notification).order_by(Notification.title))).scalars().all()
        read_map = {r.title: r.is_read for r in rows}
        assert read_map == {"A": False, "B": True}


# ------------------------------------------------------------------
# Preferences
# ------------------------------------------------------------------

class TestPreferencesProduction:
    async def test_get_preferences_default(self, session, monkeypatch):
        uid = await _create_user(session, "13900220009")
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        resp = await service.get_preferences(uid)
        assert len(resp.preferences) == 5
        types = {p.type for p in resp.preferences}
        assert types == {"followup", "system", "training", "team", "achievement"}
        assert all(p.enabled for p in resp.preferences)

    async def test_update_and_get_preference_persists(self, session, monkeypatch):
        uid = await _create_user(session, "13900220010")
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        updated = await service.update_preference(
            uid, UpdatePreferenceRequest(type="followup", enabled=False)
        )
        assert updated.enabled is False
        assert updated.type == "followup"

        # 数据库中确实有一条偏好行
        row = (await session.execute(select(NotificationPreference))).scalars().first()
        assert row is not None
        assert row.followup_enabled is False
        assert row.system_enabled is True  # 其余列保持默认

        # get_preferences 反映更新
        resp = await service.get_preferences(uid)
        pref_map = {p.type: p.enabled for p in resp.preferences}
        assert pref_map["followup"] is False
        assert pref_map["system"] is True

    async def test_update_preference_upserts_existing(self, session, monkeypatch):
        uid = await _create_user(session, "13900220011")
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        await service.update_preference(uid, UpdatePreferenceRequest(type="team", enabled=False))
        await service.update_preference(uid, UpdatePreferenceRequest(type="training", enabled=False))

        rows = (await session.execute(select(NotificationPreference))).scalars().all()
        assert len(rows) == 1  # 同一行被复用
        assert rows[0].team_enabled is False
        assert rows[0].training_enabled is False

    async def test_update_preference_unknown_type(self, session, monkeypatch):
        uid = await _create_user(session, "13900220012")
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        with pytest.raises(ValueError):
            await service.update_preference(
                uid, UpdatePreferenceRequest(type="unknown_type", enabled=True)
            )


# ------------------------------------------------------------------
# Transaction rollback
# ------------------------------------------------------------------

class TestNotificationRollback:
    async def test_mark_read_rollback_on_commit_failure(self, session, monkeypatch):
        uid = await _create_user(session, "13900220013")
        await _add_notification(session, uid, type_="system", title="N1", read=False)
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        async def _boom():
            raise RuntimeError("simulated db failure")

        original_commit = session.commit
        monkeypatch.setattr(session, "commit", _boom)
        with pytest.raises(RuntimeError):
            await service.mark_read(uid, read_all=True)
        monkeypatch.setattr(session, "commit", original_commit)

        row = (await session.execute(select(Notification))).scalars().first()
        assert row.is_read is False  # 回滚后未变成已读
