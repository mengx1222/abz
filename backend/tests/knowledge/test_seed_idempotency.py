"""Task 35 — scripts/seed.py 幂等性回归测试（backend-pg）。

覆盖目标（Task 35 Phase 3）：
1. seed 第一次运行成功（7 角色 / 21 权限 / 6 组织 / 4 用户 / 训练场景全部落库）
2. seed 第二次运行成功（不抛错、不产生重复数据）
3. 无重复数据（每个 code/name/phone 恰好 1 条）
4. 权限关系正确（角色-权限绑定与 ROLE_PERMISSIONS 定义一致；用户角色/组织映射正确）

通过环境变量 AZB_TEST_DATABASE_URL 指定真实 PostgreSQL（含 pgvector），
未设置时整个模块跳过（CI backend-pg job 提供）。
"""
import os

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Base, Organization, Role, User
from app.models.customer import Customer
from app.models.knowledge import Document, KnowledgeBase
from app.models.permission import Permission, role_permissions
from scripts.e2e_seed_knowledge import KB_DOCS, KB_NAME
from scripts.seed import (
    DEMO_USERS,
    ORGANIZATIONS,
    PERMISSIONS,
    PILOT_CUSTOMERS,
    ROLES,
    ROLE_PERMISSIONS,
    seed_database,
)

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
async def _use_test_db(monkeypatch):
    """seed_database 自建 engine 读取 settings.DATABASE_URL → 指向测试 PG。"""
    monkeypatch.setattr(settings, "DATABASE_URL", PG_URL)


async def _count(session: AsyncSession, model, column, value) -> int:
    stmt = select(func.count()).select_from(model).where(column == value)
    return (await session.execute(stmt)).scalar_one()


class TestSeedIdempotency:
    async def test_seed_first_run_creates_all(self, session: AsyncSession):
        """第一次运行：全部种子数据落库（每 code/name/phone 恰好 1 条）。"""
        await seed_database()

        for r in ROLES:
            assert await _count(session, Role, Role.code, r["code"]) == 1, f"role {r['code']}"
        for p in PERMISSIONS:
            assert await _count(session, Permission, Permission.code, p["code"]) == 1, f"permission {p['code']}"
        for o in ORGANIZATIONS:
            assert await _count(session, Organization, Organization.name, o["name"]) == 1, f"org {o['name']}"
        for u in DEMO_USERS:
            assert await _count(session, User, User.phone, u["phone"]) == 1, f"user {u['phone']}"
        # ULTIMATE Pilot Prep + RDY 阶段1：试点客户 + 产品知识库（幂等创建）
        for c in PILOT_CUSTOMERS:
            assert await _count(session, Customer, Customer.phone, c["phone"]) == 1, f"customer {c['phone']}"
        assert await _count(session, KnowledgeBase, KnowledgeBase.name, KB_NAME) == 1, "pilot KB"
        # RDY 阶段1：数据标识审计 —— 每个客户 tags 含 PILOT；合规高风险/异议案例带专属 tag
        risk = (
            await session.execute(select(Customer).where(Customer.phone == "13900000004"))
        ).scalar_one_or_none()
        assert risk is not None and risk.tags and "COMPLIANCE_RISK" in risk.tags, "compliance risk tag"
        obj = (
            await session.execute(select(Customer).where(Customer.phone == "13900000005"))
        ).scalar_one_or_none()
        assert obj is not None and obj.tags and "OBJECTION" in obj.tags, "objection tag"
        # 知识库文档数 = KB_DOCS（RDY 阶段1 = 3），metadata_ 携带 dataset_tag
        kb = (
            await session.execute(select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME))
        ).scalar_one()
        doc_count = (
            await session.execute(
                select(Document).where(Document.knowledge_base_id == kb.id)
            )
        ).scalars().all()
        assert len(doc_count) == len(KB_DOCS), f"docs {len(doc_count)} != {len(KB_DOCS)}"
        assert kb.metadata_ and kb.metadata_.get("dataset_tag") == "E2E_TEST/PILOT", "kb dataset tag"

    async def test_seed_second_run_idempotent_no_duplicates(self, session: AsyncSession):
        """第二次运行：成功且不产生重复数据（数量仍为 1）。"""
        await seed_database()

        for r in ROLES:
            assert await _count(session, Role, Role.code, r["code"]) == 1, f"role {r['code']} duplicated"
        for p in PERMISSIONS:
            assert await _count(session, Permission, Permission.code, p["code"]) == 1, f"permission {p['code']} duplicated"
        for o in ORGANIZATIONS:
            assert await _count(session, Organization, Organization.name, o["name"]) == 1, f"org {o['name']} duplicated"
        for u in DEMO_USERS:
            assert await _count(session, User, User.phone, u["phone"]) == 1, f"user {u['phone']} duplicated"
        # ULTIMATE Pilot Prep + RDY 阶段1：重跑不产生重复试点数据
        for c in PILOT_CUSTOMERS:
            assert await _count(session, Customer, Customer.phone, c["phone"]) == 1, f"customer {c['phone']} duplicated"
        assert await _count(session, KnowledgeBase, KnowledgeBase.name, KB_NAME) == 1, "pilot KB duplicated"
        # RDY 阶段1：重跑后 tags/metadata 标识仍稳定（不重复叠加）
        risk2 = (
            await session.execute(select(Customer).where(Customer.phone == "13900000004"))
        ).scalar_one_or_none()
        assert risk2 is not None and risk2.tags.count("PILOT") == 1, "tag not duplicated"
        kb2 = (
            await session.execute(select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME))
        ).scalar_one()
        assert kb2.metadata_.get("dataset_tag") == "E2E_TEST/PILOT", "kb tag stable"

    async def test_seed_permission_relationships_correct(self, session: AsyncSession):
        """权限关系：角色-权限绑定与 ROLE_PERMISSIONS 一致；用户角色/组织映射正确。"""
        await seed_database()

        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            role = (await session.execute(select(Role).where(Role.code == role_code))).scalar_one()
            bound = (
                await session.execute(
                    select(role_permissions.c.permission_id).where(role_permissions.c.role_id == role.id)
                )
            ).scalars().all()
            expected = (
                await session.execute(select(Permission.id).where(Permission.code.in_(perm_codes)))
            ).scalars().all()
            assert set(bound) == set(expected), f"role {role_code} permission bindings mismatch"

        for u in DEMO_USERS:
            user = (await session.execute(select(User).where(User.phone == u["phone"]))).scalar_one()
            role = (await session.execute(select(Role).where(Role.id == user.role_id))).scalar_one()
            org = (
                await session.execute(select(Organization).where(Organization.id == user.organization_id))
            ).scalar_one()
            assert role.code == u["role_code"], f"user {u['phone']} role"
            assert org.name == u["org_name"], f"user {u['phone']} org"
