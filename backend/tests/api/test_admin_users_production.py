"""管理后台用户管理 —— 生产分支（真实用户表）测试。

覆盖（SQLite 内存库 + dependency_overrides get_db/get_current_user）：
- 创建用户：写入真实表、密码哈希落库；重复手机号 409
- 更新用户/重置密码：new_password 落库且新密码可验证
- 禁用/启用：status 切换，禁用后登录被拒
- 列表：生产模式返回真实用户条目
"""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

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
from app.core.deps import get_current_user, get_db
from app.core.security import hash_password, verify_password
from app.main import app
from app.models import Base, Organization, Role, User
from app.models.organization import OrgType

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def env(monkeypatch):
    """生产模式（DEMO_MODE=False）+ 独立 SQLite 内存库 + 注入管理员。"""
    monkeypatch.setattr(settings, "DEMO_MODE", False)

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        now = datetime.now(timezone.utc)
        agent_role = Role(
            id=uuid.uuid4(), code="AGENT", name="代理人", level=1,
            created_at=now, updated_at=now,
        )
        admin_role = Role(
            id=uuid.uuid4(), code="SYSTEM_ADMIN", name="系统管理员", level=9,
            created_at=now, updated_at=now,
        )
        org = Organization(
            id=uuid.uuid4(), name="测试机构", type=OrgType.HQ,
            created_at=now, updated_at=now,
        )
        admin = User(
            id=uuid.uuid4(), phone="13900000000", name="管理员",
            password_hash=hash_password("adminpass123"),
            status="active", demo_mode=False,
            role_id=admin_role.id, organization_id=org.id,
            created_at=now, updated_at=now,
        )
        admin.role = admin_role
        s.add_all([agent_role, admin_role, org, admin])
        await s.commit()

        async def _override_db():
            yield s

        async def _override_current_user():
            return admin

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _override_current_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield {"client": client, "session": s, "agent_role": agent_role, "org": org}

        app.dependency_overrides.clear()

    await engine.dispose()


def _create_payload(role_id: uuid.UUID, org_id: uuid.UUID) -> dict:
    return {
        "name": "新接线员",
        "phone": "13911110000",
        "role_code": "AGENT",
        "organization_id": str(org_id),
        "initial_password": "Start@123",
    }


class TestAdminUsersProduction:
    async def test_create_user_persists_with_hashed_password(self, env):
        client, session = env["client"], env["session"]
        payload = _create_payload(env["agent_role"].id, env["org"].id)
        resp = await client.post("/api/v1/admin/users", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["phone"] == "13911110000"
        assert data["role_code"] == "AGENT"

        user = (
            await session.execute(select(User).where(User.phone == "13911110000"))
        ).scalar_one_or_none()
        assert user is not None
        assert verify_password("Start@123", user.password_hash)

    async def test_create_user_duplicate_phone_409(self, env):
        client, session = env["client"], env["session"]
        payload = _create_payload(env["agent_role"].id, env["org"].id)
        await client.post("/api/v1/admin/users", json=payload)
        resp = await client.post("/api/v1/admin/users", json=payload)
        assert resp.status_code == 409

    async def test_update_user_reset_password(self, env):
        client, session = env["client"], env["session"]
        payload = _create_payload(env["agent_role"].id, env["org"].id)
        created = (await client.post("/api/v1/admin/users", json=payload)).json()["data"]

        resp = await client.put(
            f"/api/v1/admin/users/{created['id']}",
            json={"name": "改名接线员", "new_password": "NewPass@456"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "改名接线员"

        user = (
            await session.execute(select(User).where(User.phone == "13911110000"))
        ).scalar_one()
        assert verify_password("NewPass@456", user.password_hash)
        assert not verify_password("Start@123", user.password_hash)

    async def test_disable_blocks_login_and_enable_restores(self, env):
        client = env["client"]
        payload = _create_payload(env["agent_role"].id, env["org"].id)
        created = (await client.post("/api/v1/admin/users", json=payload)).json()["data"]

        resp = await client.post(
            f"/api/v1/admin/users/{created['id']}/disable",
            json={"reason": "离职"},
        )
        assert resp.status_code == 200

        # 登录被拒（生产分支：状态非 active）
        login = await client.post(
            "/api/v1/auth/login",
            json={"phone": "13911110000", "password": "Start@123"},
        )
        assert login.status_code == 401

        resp = await client.post(f"/api/v1/admin/users/{created['id']}/enable")
        assert resp.status_code == 200

    async def test_list_users_production_returns_db_rows(self, env):
        client = env["client"]
        payload = _create_payload(env["agent_role"].id, env["org"].id)
        await client.post("/api/v1/admin/users", json=payload)

        resp = await client.get("/api/v1/admin/users?keyword=新接线员")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert any(u["phone"] == "13911110000" for u in items)