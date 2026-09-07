"""修改自身密码（change_password）单元测试 —— 生产分支真实逻辑。

覆盖（SQLite + settings.DEMO_MODE=False，保持真实 Service / Repo wiring）：
- 正常修改：原密码校验通过 → 新密码哈希落库 → 可用新密码验证
- 原密码错误 / 原哈希为空 → ValueError("原密码错误")
- 新密码 < 8 位 → ValueError
- 新密码与原密码相同 → ValueError
- 演示账号（user.demo_mode=True）→ 明确拒绝
- 全局演示模式（settings.DEMO_MODE=True）→ 明确拒绝
"""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
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
from app.core.security import hash_password, verify_password
from app.models import Base, Organization, Role, User
from app.models.organization import OrgType
from app.services.auth_service import AuthService

pytestmark = pytest.mark.integration

OLD_PASSWORD = "oldpass123"
NEW_PASSWORD = "newpass4567"


@pytest_asyncio.fixture
async def db_session(monkeypatch):
    """生产模式（DEMO_MODE=False）+ 独立 SQLite 内存库。"""
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
        org = Organization(
            id=uuid.uuid4(), name="测试机构", type=OrgType.HQ,
            created_at=now, updated_at=now,
        )
        role = Role(
            id=uuid.uuid4(), code="AGENT", name="代理人", level=1,
            created_at=now, updated_at=now,
        )
        user = User(
            id=uuid.uuid4(), phone="13911112222", name="测试改密",
            password_hash=hash_password(OLD_PASSWORD),
            status="active", demo_mode=False,
            role_id=role.id, organization_id=org.id,
            created_at=now, updated_at=now,
        )
        s.add_all([org, role, user])
        await s.commit()
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    result = await db_session.execute(select(User).where(User.phone == "13911112222"))
    return result.scalar_one()


class TestChangePasswordProduction:
    async def test_change_password_success(self, db_session, sample_user: User):
        """正常修改：哈希落库，且新密码可验证。"""
        await AuthService(db_session).change_password(sample_user, OLD_PASSWORD, NEW_PASSWORD)

        assert sample_user.password_hash is not None
        assert verify_password(NEW_PASSWORD, sample_user.password_hash)
        assert not verify_password(OLD_PASSWORD, sample_user.password_hash)

    async def test_wrong_old_password(self, db_session, sample_user: User):
        with pytest.raises(ValueError, match="原密码错误"):
            await AuthService(db_session).change_password(sample_user, "wrong-old", NEW_PASSWORD)

    async def test_new_password_too_short(self, db_session, sample_user: User):
        with pytest.raises(ValueError, match="至少需要 8 位"):
            await AuthService(db_session).change_password(sample_user, OLD_PASSWORD, "a1b2c3")

    async def test_new_password_same_as_old(self, db_session, sample_user: User):
        with pytest.raises(ValueError, match="不能与原密码相同"):
            await AuthService(db_session).change_password(sample_user, OLD_PASSWORD, OLD_PASSWORD)

    async def test_demo_user_rejected(self, db_session, sample_user: User):
        sample_user.demo_mode = True
        await db_session.commit()

        with pytest.raises(ValueError, match="演示账号不支持修改密码"):
            await AuthService(db_session).change_password(sample_user, OLD_PASSWORD, NEW_PASSWORD)

    async def test_global_demo_mode_rejected(self, db_session, sample_user: User, monkeypatch):
        monkeypatch.setattr(settings, "DEMO_MODE", True)

        with pytest.raises(ValueError, match="演示账号不支持修改密码"):
            await AuthService(db_session).change_password(sample_user, OLD_PASSWORD, NEW_PASSWORD)

    async def test_empty_password_hash(self, db_session, sample_user: User):
        sample_user.password_hash = None
        await db_session.commit()

        with pytest.raises(ValueError, match="原密码错误"):
            await AuthService(db_session).change_password(sample_user, OLD_PASSWORD, NEW_PASSWORD)
