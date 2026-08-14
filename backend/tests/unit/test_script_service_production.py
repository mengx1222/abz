"""Script Service Production 路径测试。

在 DEMO_MODE=false 下直接驱动 ScriptService，使用 SQLite 内存库
(Base.metadata.create_all) 验证生产路径：
- 话术创建（持久化 + created_by 归属 + 自动合规检查）
- 话术列表（按创建者隔离 + 多维筛选）
- 话术详情（归属校验 / 不存在）
- 话术更新（归属校验 + 内容变更重新合规）
- 话术删除（软删除 + 归属校验）
- 收藏切换（ScriptFavorite 行 + 计数增减）
- 权限隔离

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
from app.models import Base, Script, ScriptFavorite, User
from app.services.script_service import ScriptService

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


async def _make_production_service(session: AsyncSession, monkeypatch) -> ScriptService:
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    return ScriptService(session=session)


def _script_data(**overrides) -> dict:
    data = {
        "title": "张先生医疗险-专业型",
        "customer_context": {"name": "张先生", "age": 35, "stage": "needs_analysis"},
        "style": "professional",
        "content": "张先生，从专业角度分析百万医疗险的性价比。",
        "product_type": "医疗险",
        "status": "draft",
    }
    data.update(overrides)
    return data


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------

class TestScriptCreateProduction:
    async def test_create_script_persists(self, session, monkeypatch):
        uid = await _create_user(session, "13900110001")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        script = await service.create_script(_script_data(), user_id=str(uid))
        assert script["id"]
        assert script["style"] == "professional"
        assert script["compliance_status"] in ("green", "yellow", "red")

        row = (await session.execute(select(Script))).scalars().first()
        assert row is not None
        assert str(row.created_by) == str(uid)
        assert row.title == "张先生医疗险-专业型"

    async def test_create_script_auto_compliance(self, session, monkeypatch):
        uid = await _create_user(session, "13900110002")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        script = await service.create_script(
            _script_data(content="买这个保险保证有收益，肯定能通过核保"),
            user_id=str(uid),
        )
        assert script["compliance_status"] == "red"
        assert script["compliance_issues"]["status"] == "red"


# ------------------------------------------------------------------
# List / Get
# ------------------------------------------------------------------

class TestScriptReadProduction:
    async def test_get_scripts_scoped_to_owner(self, session, monkeypatch):
        alice = await _create_user(session, "13900110003")
        bob = await _create_user(session, "13900110004")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        await service.create_script(_script_data(title="Alice话术"), user_id=str(alice))
        await service.create_script(_script_data(title="Bob话术"), user_id=str(bob))

        alice_list = await service.get_scripts(user_id=str(alice))
        assert len(alice_list) == 1
        assert alice_list[0]["title"] == "Alice话术"
        bob_list = await service.get_scripts(user_id=str(bob))
        assert len(bob_list) == 1
        assert bob_list[0]["title"] == "Bob话术"

    async def test_get_scripts_filters(self, session, monkeypatch):
        uid = await _create_user(session, "13900110005")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        await service.create_script(
            _script_data(title="百万医疗亲和话术", style="affinity", product_type="医疗险", status="draft"),
            user_id=str(uid),
        )
        await service.create_script(
            _script_data(title="少儿重疾专业话术", style="professional", product_type="重疾险", status="published"),
            user_id=str(uid),
        )

        assert len(await service.get_scripts({"style": "affinity"}, user_id=str(uid))) == 1
        assert len(await service.get_scripts({"product_type": "重疾险"}, user_id=str(uid))) == 1
        assert len(await service.get_scripts({"status": "draft"}, user_id=str(uid))) == 1
        assert len(await service.get_scripts({"search": "亲和"}, user_id=str(uid))) == 1
        assert len(await service.get_scripts(user_id=str(uid))) == 2

    async def test_get_script_detail_and_permission(self, session, monkeypatch):
        alice = await _create_user(session, "13900110006")
        bob = await _create_user(session, "13900110007")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        created = await service.create_script(
            _script_data(content="详细内容"), user_id=str(alice)
        )

        detail = await service.get_script(created["id"], user_id=str(alice))
        assert detail is not None
        assert detail["content"] == "详细内容"
        assert "version" in detail

        # 越权 / 不存在
        assert await service.get_script(created["id"], user_id=str(bob)) is None
        assert await service.get_script(str(uuid.uuid4()), user_id=str(alice)) is None
        assert await service.get_script("not-a-uuid", user_id=str(alice)) is None


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------

class TestScriptUpdateProduction:
    async def test_update_script_owned(self, session, monkeypatch):
        uid = await _create_user(session, "13900110008")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        created = await service.create_script(_script_data(), user_id=str(uid))

        updated = await service.update_script(
            created["id"],
            {"title": "新标题", "content": "买这个保险保证有收益"},
            user_id=str(uid),
        )
        assert updated is not None
        assert updated["title"] == "新标题"
        assert updated["compliance_status"] == "red"

    async def test_update_script_not_owned(self, session, monkeypatch):
        alice = await _create_user(session, "13900110009")
        bob = await _create_user(session, "13900110010")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        created = await service.create_script(_script_data(), user_id=str(alice))

        assert await service.update_script(created["id"], {"title": "x"}, user_id=str(bob)) is None
        assert await service.update_script(created["id"], {"title": "x"}, user_id=str(alice)) is not None


# ------------------------------------------------------------------
# Delete
# ------------------------------------------------------------------

class TestScriptDeleteProduction:
    async def test_delete_script_owned(self, session, monkeypatch):
        uid = await _create_user(session, "13900110011")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        created = await service.create_script(_script_data(), user_id=str(uid))

        assert await service.delete_script(created["id"], user_id=str(uid)) is True
        # 软删除后不可再读取/列表
        assert await service.get_script(created["id"], user_id=str(uid)) is None
        assert await service.get_scripts(user_id=str(uid)) == []

    async def test_delete_script_not_owned_or_missing(self, session, monkeypatch):
        alice = await _create_user(session, "13900110012")
        bob = await _create_user(session, "13900110013")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        created = await service.create_script(_script_data(), user_id=str(alice))

        assert await service.delete_script(created["id"], user_id=str(bob)) is False
        assert await service.delete_script(str(uuid.uuid4()), user_id=str(alice)) is False


# ------------------------------------------------------------------
# Favorite
# ------------------------------------------------------------------

class TestScriptFavoriteProduction:
    async def test_toggle_favorite_counts(self, session, monkeypatch):
        uid = await _create_user(session, "13900110014")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        created = await service.create_script(_script_data(), user_id=str(uid))

        # 收藏
        fav_1 = await service.toggle_favorite(created["id"], user_id=str(uid))
        assert fav_1["favorited_count"] == 1
        rows = (await session.execute(select(ScriptFavorite))).scalars().all()
        assert len(rows) == 1

        # 取消收藏
        fav_2 = await service.toggle_favorite(created["id"], user_id=str(uid))
        assert fav_2["favorited_count"] == 0
        rows = (await session.execute(select(ScriptFavorite))).scalars().all()
        assert len(rows) == 0

    async def test_toggle_favorite_missing(self, session, monkeypatch):
        uid = await _create_user(session, "13900110015")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        assert await service.toggle_favorite(str(uuid.uuid4()), user_id=str(uid)) is None


# ------------------------------------------------------------------
# Transaction rollback
# ------------------------------------------------------------------

class TestScriptRollback:
    async def test_create_script_rollback_on_commit_failure(self, session, monkeypatch):
        uid = await _create_user(session, "13900110016")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        async def _boom():
            raise RuntimeError("simulated db failure")

        original_commit = session.commit
        monkeypatch.setattr(session, "commit", _boom)
        with pytest.raises(RuntimeError):
            await service.create_script(_script_data(), user_id=str(uid))
        monkeypatch.setattr(session, "commit", original_commit)

        rows = (await session.execute(select(Script))).scalars().all()
        assert rows == []
