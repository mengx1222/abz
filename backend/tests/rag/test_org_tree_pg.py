"""Task 26 — Production 模式组织树递归实测（backend-pg，真实 async + PG）。

背景（审计 docs/test-infrastructure-audit.md §RBAC-Org）：
DataPermissionChecker._collect_child_org_ids 依赖 `Organization.children`
（lazy="selectin"）在 async 上下文同步访问。若查询 User 时未 eager-load 组织树，
SQLAlchemy async 会抛 MissingGreenlet 并被 `except Exception` 静默吞掉 →
HQ_ADMIN/BRANCH_ADMIN 的可访问范围**退化为仅本组织**（与文档「本机构 + 下属机构」
语义不符）。现有覆盖：
- unit（test_authorization.py）：内存构造 Organization 对象并直接赋 .children（不触发 DB 加载）
- test_org_scope.py：monkeypatch filter_accessible_org_ids（绕过真实实现）
→ 均未覆盖「真实 PG + async + 从 DB 查询用户」路径。

本文件在真实 PG + DEMO_MODE=false 下验证组织树递归：
1. HQ_ADMIN@HQ → 应含 HQ + Branch + Team（全子树）
2. BRANCH_ADMIN@Branch → 应含本 Branch + Team（不含兄弟 Branch）
3. TEAM_LEADER@Team → 应含本 Team

通过环境变量 AZB_TEST_DATABASE_URL 指定真实 PostgreSQL（含 pgvector），
未设置时跳过（CI backend-pg job 提供）。
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Base, Organization, Role, User
from app.models.organization import OrgType
from app.core.authorization import DataPermissionChecker
from sqlalchemy.orm import selectinload

PG_URL = os.environ.get("AZB_TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not PG_URL, reason="AZB_TEST_DATABASE_URL not set"),
]


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(PG_URL, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
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
    """conftest 默认 DEMO_MODE=true；本测试必须走真实生产分支。"""
    monkeypatch.setattr(settings, "DEMO_MODE", False)


async def _get_or_create_role(session: AsyncSession, code: str, name: str) -> Role:
    role = (await session.execute(select(Role).where(Role.code == code))).scalars().first()
    if role is None:
        role = Role(code=code, name=name, level=1)
        session.add(role)
        await session.flush()
    return role


async def _seed_tree(session: AsyncSession) -> dict:
    """构造 HQ → 上海分公司 → 浦东团队 三层组织树 + 用户，返回 {orgs, users, roles}。"""
    suffix = uuid.uuid4().hex[:6]

    hq = Organization(name=f"总部-{suffix}", type=OrgType.HQ)
    branch = Organization(name=f"上海分公司-{suffix}", type=OrgType.BRANCH)
    team = Organization(name=f"浦东团队-{suffix}", type=OrgType.TEAM)
    other_branch = Organization(name=f"北京分公司-{suffix}", type=OrgType.BRANCH)

    session.add_all([hq, branch, team, other_branch])
    await session.flush()

    branch.parent_id = hq.id
    team.parent_id = branch.id
    # 注意：Organization.children 是 lazy=selectin，此处显式加载树以便后续断言对比
    await session.flush()

    role_hq = await _get_or_create_role(session, "HQ_ADMIN", "总部管理员")
    role_branch = await _get_or_create_role(session, "BRANCH_ADMIN", "分公司管理员")
    role_team = await _get_or_create_role(session, "TEAM_LEADER", "团队长")

    def _user(phone: str, role: Role, org: Organization) -> User:
        u = User(
            phone=f"136{suffix}{phone}", name=f"用户{phone}",
            password_hash=None, role_id=role.id, organization_id=org.id,
            status="active", demo_mode=False,
        )
        session.add(u)
        return u

    hq_user = _user("01", role_hq, hq)
    branch_user = _user("02", role_branch, branch)
    team_leader = _user("03", role_team, team)
    await session.commit()

    return {
        "hq": hq, "branch": branch, "team": team, "other_branch": other_branch,
        "hq_user": hq_user, "branch_user": branch_user, "team_leader": team_leader,
    }


async def _load_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    """从 DB 重新查询用户，加载方式与 get_current_user 一致（Task 26 修复：
    嵌套 selectinload 组织树，避免 async 下 org.children MissingGreenlet）。"""
    return (
        await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                # 与 get_current_user 一致：org → children（Branch）→ children（Team）
                selectinload(User.organization)
                .selectinload(Organization.children)
                .selectinload(Organization.children),
                selectinload(User.team),
            )
        )
    ).scalars().one()


class TestOrgTreeProduction:
    async def test_hq_admin_sees_full_subtree(self, session: AsyncSession):
        """HQ_ADMIN@HQ 可访问 HQ + Branch + Team（真实 DB 组织树递归）。"""
        data = await _seed_tree(session)
        user = await _load_user(session, data["hq_user"].id)
        checker = DataPermissionChecker(user)
        orgs = checker.filter_accessible_org_ids()

        assert str(data["hq"].id) in orgs, "HQ_ADMIN 应含本组织"
        assert str(data["branch"].id) in orgs, "HQ_ADMIN 应含下级分公司（递归失效？）"
        assert str(data["team"].id) in orgs, "HQ_ADMIN 应含孙级团队（递归失效？）"

    async def test_branch_admin_sees_branch_subtree_only(self, session: AsyncSession):
        """BRANCH_ADMIN@上海 可访问本 Branch + Team，不可访问北京 Branch。"""
        data = await _seed_tree(session)
        user = await _load_user(session, data["branch_user"].id)
        checker = DataPermissionChecker(user)
        orgs = checker.filter_accessible_org_ids()

        assert str(data["branch"].id) in orgs, "BRANCH_ADMIN 应含本组织"
        assert str(data["team"].id) in orgs, "BRANCH_ADMIN 应含下级团队（递归失效？）"
        assert str(data["other_branch"].id) not in orgs, "BRANCH_ADMIN 不应访问兄弟分公司"

    async def test_team_leader_sees_own_team(self, session: AsyncSession):
        """TEAM_LEADER@浦东团队 仅本团队。"""
        data = await _seed_tree(session)
        user = await _load_user(session, data["team_leader"].id)
        checker = DataPermissionChecker(user)
        orgs = checker.filter_accessible_org_ids()

        assert str(data["team"].id) in orgs
        assert str(data["branch"].id) not in orgs, "TEAM_LEADER 不应越级访问分公司"
        assert str(data["hq"].id) not in orgs
