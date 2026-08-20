"""Task 44 P0-1 — 生产 AGENT 客户访问（assigned_to 归属 + 列表/详情同源）。

覆盖：
A. 单元（checker 级，无 DB）：
   1. 生产 AGENT 可访问本人 assigned 客户
   2. 生产 AGENT 不可访问他人 assigned 客户
   3. 生产 AGENT 未带 assigned_to（无归属）不可访问
   4. 生产 AGENT 跨组织 assigned 不可访问（兼验 organization_id）
   5. restrict_to_own_customers 语义（prod AGENT True / demo AGENT False / HQ prod False）
   6. demo AGENT 同机构可见（不回归）
   7. HQ_ADMIN 生产可访问本机构（不回归）

B. PG 集成（服务级，backend-pg job 提供 AZB_TEST_DATABASE_URL）：
   8. 生产 AGENT 列表仅含本人 assigned（同源过滤）
   9. 生产 AGENT 详情本人可见 / 他人 404 语义（返回 None）
   10. 生产 AGENT 互动/跟进他人客户被拒（返回 None）
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.authorization import DataPermissionChecker
from app.models.customer import Customer
from app.models.organization import Organization, OrgType
from app.models.role import Role
from app.models.user import User
from app.core.config import settings

PG_URL = os.environ.get("AZB_TEST_DATABASE_URL", "")

# ------------------------------------------------------------------
# A. 单元测试（checker 级）
# ------------------------------------------------------------------

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")
NOW = datetime.now(timezone.utc)


def _make_user(role_code="AGENT", org_id=None, team_id=None, demo_mode=True, user_id=None):
    uid = user_id or uuid.uuid4()
    oid = org_id or ORG_ID
    user = User(
        id=uid,
        phone="13800138000",
        name="测试用户",
        password_hash="",
        status="active",
        demo_mode=demo_mode,
        role_id=ROLE_ID,
        organization_id=oid,
        team_id=team_id,
        created_at=NOW,
        updated_at=NOW,
    )
    user.role = Role(id=ROLE_ID, code=role_code, name=role_code, level=1, created_at=NOW, updated_at=NOW)
    user.organization = Organization(id=oid, name="测试组织", type=OrgType.HQ, created_at=NOW, updated_at=NOW)
    return user


class TestProductionAgentCustomerAccess:
    def test_prod_agent_own_assigned_ok(self, monkeypatch):
        """生产 AGENT 可访问本人 assigned 客户（兼验同组织）。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        agent = _make_user(role_code="AGENT", demo_mode=False, user_id=uuid.uuid4())
        checker = DataPermissionChecker(agent)
        assert checker.can_access_customer(str(ORG_ID), str(agent.id)) is True

    def test_prod_agent_other_assigned_denied(self, monkeypatch):
        """生产 AGENT 不可访问他人 assigned 客户。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        agent = _make_user(role_code="AGENT", demo_mode=False, user_id=uuid.uuid4())
        checker = DataPermissionChecker(agent)
        other = uuid.uuid4()
        assert checker.can_access_customer(str(ORG_ID), str(other)) is False

    def test_prod_agent_no_assigned_denied(self, monkeypatch):
        """生产 AGENT 未带 assigned_to（无归属）不可访问。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        agent = _make_user(role_code="AGENT", demo_mode=False, user_id=uuid.uuid4())
        checker = DataPermissionChecker(agent)
        assert checker.can_access_customer(str(ORG_ID)) is False

    def test_prod_agent_cross_org_assigned_denied(self, monkeypatch):
        """生产 AGENT 跨组织 assigned 不可访问（兼验 organization_id）。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        agent = _make_user(role_code="AGENT", demo_mode=False, user_id=uuid.uuid4())
        checker = DataPermissionChecker(agent)
        assert checker.can_access_customer(str(OTHER_ORG_ID), str(agent.id)) is False

    def test_restrict_to_own_customers(self, monkeypatch):
        """restrict_to_own_customers：prod 环境 AGENT True；demo 环境 demo AGENT False；HQ prod False。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        prod_agent = _make_user(role_code="AGENT", demo_mode=False)
        hq = _make_user(role_code="HQ_ADMIN", demo_mode=False)
        assert DataPermissionChecker(prod_agent).restrict_to_own_customers() is True
        assert DataPermissionChecker(hq).restrict_to_own_customers() is False
        # demo 环境（DEMO_MODE=True）+ demo 用户 → 宽松（不 restrict）
        monkeypatch.setattr(settings, "DEMO_MODE", True)
        demo_agent = _make_user(role_code="AGENT", demo_mode=True)
        assert DataPermissionChecker(demo_agent).restrict_to_own_customers() is False
        # production 环境 + demo 用户标记 → 仍 restrict（ULTIMATE Pilot：不绕过）
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        prod_env_demo_user = _make_user(role_code="AGENT", demo_mode=True)
        assert DataPermissionChecker(prod_env_demo_user).restrict_to_own_customers() is True

    def test_demo_agent_org_visible_no_regression(self, monkeypatch):
        """demo 环境（DEMO_MODE=True）+ demo AGENT：同机构可见（demo 宽松不回归）。"""
        monkeypatch.setattr(settings, "DEMO_MODE", True)
        agent = _make_user(role_code="AGENT", demo_mode=True, user_id=uuid.uuid4())
        checker = DataPermissionChecker(agent)
        assert checker.can_access_customer(str(ORG_ID)) is True
        assert checker.can_access_customer(str(OTHER_ORG_ID)) is False

    def test_hq_admin_prod_no_regression(self, monkeypatch):
        """HQ_ADMIN 生产本机构可访问（不回归）。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        hq = _make_user(role_code="HQ_ADMIN", demo_mode=False)
        checker = DataPermissionChecker(hq)
        assert checker.can_access_customer(str(ORG_ID)) is True


# ------------------------------------------------------------------
# B. PG 集成测试（服务级）
# ------------------------------------------------------------------

pytestmark_pg = [
    pytest.mark.integration,
    pytest.mark.skipif(not PG_URL, reason="AZB_TEST_DATABASE_URL not set"),
]


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(PG_URL, poolclass=NullPool)
    async with eng.begin() as conn:
        from app.models import Base
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture(autouse=True)
async def _production_mode(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)


async def _mk_role(session, code):
    role = (await session.execute(select(Role).where(Role.code == code))).scalars().first()
    if role is None:
        role = Role(code=code, name=code, level=1)
        session.add(role)
        await session.flush()
    return role


async def _mk_user(session, role, phone, org_id, name="测试"):
    user = User(
        phone=phone, name=name, password_hash="x", status="active",
        demo_mode=False, role_id=role.id, organization_id=org_id,
    )
    session.add(user)
    await session.flush()
    return user


async def _mk_customer(session, name, org_id, assigned_to):
    c = Customer(
        name=name, phone="13900000000", customer_type="active",
        current_stage="initial_contact", intention_level=1,
        assigned_to=assigned_to, organization_id=org_id,
    )
    session.add(c)
    await session.flush()
    return c


@pytest.mark.integration
@pytest.mark.skipif(not PG_URL, reason="AZB_TEST_DATABASE_URL not set")
class TestCustomerServiceProductionAgent:
    @pytest_asyncio.fixture(autouse=True)
    async def _seed(self, session: AsyncSession):
        from app.models import Organization as OrgModel
        org = OrgModel(id=ORG_ID, name="测试机构", type=OrgType.BRANCH)
        session.add(org)
        role = await _mk_role(session, "AGENT")
        self.agent_a = await _mk_user(session, role, "13800000001", ORG_ID, name="代理人A")
        self.agent_b = await _mk_user(session, role, "13800000002", ORG_ID, name="代理人B")
        self.c_own = await _mk_customer(session, "客户A-自有", ORG_ID, self.agent_a.id)
        self.c_other = await _mk_customer(session, "客户B-他人", ORG_ID, self.agent_b.id)
        await session.commit()

    async def test_list_only_own(self, session: AsyncSession):
        """生产 AGENT 列表仅含本人 assigned 客户（同源过滤）。"""
        from app.services.customer_service import CustomerService
        svc = CustomerService(session)
        items, total = await svc.list_customers(current_user=self.agent_a)
        ids = {i["id"] for i in items}
        assert str(self.c_own.id) in ids
        assert str(self.c_other.id) not in ids
        assert total == 1

    async def test_detail_own_ok_other_none(self, session: AsyncSession):
        """生产 AGENT 详情：本人可见 / 他人返回 None（404 语义）。"""
        from app.services.customer_service import CustomerService
        svc = CustomerService(session)
        own = await svc.get_customer(self.c_own.id, current_user=self.agent_a)
        assert own is not None and own["name"] == "客户A-自有"
        other = await svc.get_customer(self.c_other.id, current_user=self.agent_a)
        assert other is None

    async def test_interaction_other_denied(self, session: AsyncSession):
        """生产 AGENT 对他人客户添加互动被拒（返回 None）。"""
        from app.schemas.customer import CustomerInteractionCreate
        from app.services.customer_service import CustomerService
        svc = CustomerService(session)
        data = CustomerInteractionCreate(type="phone", direction="outbound", content="测试互动")
        res = await svc.add_interaction(
            self.c_other.id, data, user_id=self.agent_a.id, current_user=self.agent_a,
        )
        assert res is None
        # 本人客户可正常添加（证明判定是归属而非全局拒绝）
        ok = await svc.add_interaction(
            self.c_own.id, data, user_id=self.agent_a.id, current_user=self.agent_a,
        )
        assert ok is not None

    async def test_followup_other_denied(self, session: AsyncSession):
        """生产 AGENT 对他人客户添加跟进被拒（返回 None）。"""
        from datetime import datetime as _dt, timezone as _tz
        from app.schemas.customer import CustomerFollowupCreate
        from app.services.customer_service import CustomerService
        svc = CustomerService(session)
        data = CustomerFollowupCreate(
            scheduled_date=_dt.now(_tz.utc), status="pending", content="测试跟进",
        )
        res = await svc.add_followup(
            self.c_other.id, data, user_id=self.agent_a.id, current_user=self.agent_a,
        )
        assert res is None
        ok = await svc.add_followup(
            self.c_own.id, data, user_id=self.agent_a.id, current_user=self.agent_a,
        )
        assert ok is not None

    async def test_update_other_denied(self, session: AsyncSession):
        """生产 AGENT 更新他人客户被拒（返回 None）。"""
        from app.schemas.customer import CustomerUpdate
        from app.services.customer_service import CustomerService
        svc = CustomerService(session)
        data = CustomerUpdate(notes="越权修改")
        res = await svc.update_customer(
            self.c_other.id, data, user_id=self.agent_a.id, current_user=self.agent_a,
        )
        assert res is None

    async def test_delete_other_denied(self, session: AsyncSession):
        """生产 AGENT 删除他人客户被拒（返回 False）。"""
        from app.services.customer_service import CustomerService
        svc = CustomerService(session)
        ok = await svc.delete_customer(self.c_other.id, current_user=self.agent_a)
        assert ok is False

    async def test_ai_analysis_other_denied(self, session: AsyncSession):
        """ULTIMATE P0-5：他人客户触发 AI 分析 → “客户不存在”（无权限 404 语义）。"""
        from app.services.customer_service import CustomerService
        svc = CustomerService(session)
        events = []
        async for ev in svc.ai_analysis_stream(
            self.c_other.id, current_user=self.agent_a,
        ):
            events.append(ev)
        joined = "\n".join(events)
        assert "客户不存在" in joined
        assert "analysis_start" not in joined  # 未进入分析流程

    async def test_ai_analysis_own_allowed(self, session: AsyncSession):
        """ULTIMATE P0-5：本人客户可进入分析流程（analysis_start 事件）。"""
        from app.services.customer_service import CustomerService
        svc = CustomerService(session)
        seen_start = False
        async for ev in svc.ai_analysis_stream(
            self.c_own.id, current_user=self.agent_a,
        ):
            if "analysis_start" in ev:
                seen_start = True
                break  # 在 gateway 调用前停止（避免真实 AI 依赖）
        assert seen_start is True
