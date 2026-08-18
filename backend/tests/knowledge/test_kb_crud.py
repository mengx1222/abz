"""Task 21 — Knowledge Base CRUD Production 集成测试（PostgreSQL + pgvector）。

通过环境变量 AZB_TEST_DATABASE_URL 指定真实 PostgreSQL（含 pgvector），
未设置时整个模块跳过（CI backend-pg job 提供）。

覆盖用例（任务矩阵 7 项）：
1. create success —— org/roles/metadata 落库字段验证
2. list isolation —— 按 accessible_org_ids 过滤
3. update permission —— API 层：非创建者 403 / 创建者 200（写权限语义）
4. delete cascade —— 物理删除级联删 documents/document_chunks
5. organization scope —— AGENT@A 可访问、AGENT@B 不可（API 层，DataPermissionChecker 真实链路）
6. role scope —— allowed_roles=["AGENT"]：AGENT 可见、HQ_ADMIN 不可见（repo 层过滤）
7. duplicate name handling —— 同名冲突（name_exists / API 409）
"""
import os
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.main import app
from app.models import (
    Base,
    Document,
    DocumentChunk,
    KnowledgeBase,
    Organization,
    Role,
    User,
)
from app.models.organization import OrgType
from app.repositories.knowledge_repository import KnowledgeBaseRepository

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
    """conftest 默认 DEMO_MODE=true；KB CRUD 测试必须走真实生产分支。"""
    monkeypatch.setattr(settings, "DEMO_MODE", False)


async def _get_or_create_role(session: AsyncSession, code: str, name: str) -> Role:
    role = (await session.execute(select(Role).where(Role.code == code))).scalars().first()
    if role is None:
        role = Role(code=code, name=name, level=1)
        session.add(role)
        await session.flush()
    return role


async def _seed(session: AsyncSession) -> dict:
    """创建 org A/B、角色 AGENT/HQ_ADMIN、用户 agent_a/agent_b/hq_a。"""
    suffix = uuid.uuid4().hex[:6]
    org_a = Organization(name=f"组织A-{suffix}", type=OrgType.BRANCH)
    org_b = Organization(name=f"组织B-{suffix}", type=OrgType.BRANCH)
    session.add_all([org_a, org_b])
    await session.flush()

    role_agent = await _get_or_create_role(session, "AGENT", "代理人")
    role_hq = await _get_or_create_role(session, "HQ_ADMIN", "总部管理员")

    def _user(phone: str, role: Role, org: Organization) -> User:
        u = User(
            phone=phone, name=f"用户{phone[-4:]}", password_hash=None,
            role_id=role.id, organization_id=org.id,
            status="active", demo_mode=False,
        )
        u.role = role
        u.organization = org
        session.add(u)
        return u

    # 唯一随机 phone：与 ingestion/permission 测试的 139 前缀格式彻底隔离
    def _rand_phone() -> str:
        return "17" + str(uuid.uuid4().int)[:11]

    agent_a = _user(_rand_phone(), role_agent, org_a)
    agent_b = _user(_rand_phone(), role_agent, org_b)
    hq_a = _user(_rand_phone(), role_hq, org_a)
    await session.flush()
    return {
        "org_a": org_a, "org_b": org_b,
        "agent_a": agent_a, "agent_b": agent_b, "hq_a": hq_a,
    }


@pytest_asyncio.fixture
async def api(session):
    """API 客户端（override get_db → 测试 session；get_current_user 按用例设置）。"""

    async def _get_db():
        yield session

    async def _current_user():
        return None  # 由每个用例 override

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = _current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestKnowledgeBaseCrud:
    """任务矩阵 7 用例。"""

    # 1. create success
    async def test_create_success(self, session):
        data = await _seed(session)
        repo = KnowledgeBaseRepository(session)
        kb = await repo.create_knowledge_base(
            name="产品知识库",
            description="测试描述",
            category="product",
            organization_id=data["org_a"].id,
            allowed_roles=["AGENT"],
            metadata_={"owner": "max", "env": "test"},
            created_by=data["agent_a"].id,
        )
        await session.commit()
        assert kb.id is not None
        assert kb.name == "产品知识库"
        assert kb.status == "draft"
        assert kb.organization_id == data["org_a"].id
        assert kb.allowed_roles == ["AGENT"]
        assert kb.metadata_ == {"owner": "max", "env": "test"}
        assert kb.version == 1
        assert kb.document_count == 0
        # 落库验证
        row = (await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb.id)
        )).scalar_one()
        assert row.name == "产品知识库"
        assert str(row.organization_id) == str(data["org_a"].id)

    # 2. list isolation（org 过滤）
    async def test_list_isolation(self, session):
        data = await _seed(session)
        repo = KnowledgeBaseRepository(session)
        kb_a = await repo.create_knowledge_base(
            name="A组织产品库", organization_id=data["org_a"].id, created_by=data["agent_a"].id,
        )
        await repo.create_knowledge_base(
            name="B组织产品库", organization_id=data["org_b"].id, created_by=data["agent_b"].id,
        )
        shared = await repo.create_knowledge_base(
            name="共享话术库", organization_id=None, created_by=data["hq_a"].id,
        )
        await session.commit()

        records, total = await repo.list_knowledge_bases(
            user_roles=["AGENT"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        ids = {str(r.id) for r in records}
        assert str(kb_a.id) in ids, "org A KB 应可见"
        assert shared is not None and str(shared.id) in ids, "共享 KB（org=NULL）应可见"
        assert "B组织产品库" not in {r.name for r in records}, "org B KB 不应可见"
        assert total == 2

    # 3. update permission（API 层：创建者 200 / 同组织非创建者 403）
    async def test_update_permission(self, session, api):
        data = await _seed(session)
        await session.commit()

        async def _as_user(user):
            async def _cu():
                return user
            app.dependency_overrides[get_current_user] = _cu

        # 创建者创建 KB
        await _as_user(data["agent_a"])
        resp = await api.post("/api/v1/admin/knowledge-bases", json={
            "name": "权限测试库", "description": "", "category": "training",
        })
        assert resp.status_code == 200, resp.text
        kb_id = resp.json()["data"]["id"]

        # 同组织另一 AGENT（非创建者）update → 403
        other = User(
            id=uuid.uuid4(), phone="17" + str(uuid.uuid4().int)[:11], name="其他代理人",
            password_hash=None, role_id=data["agent_a"].role_id,
            organization_id=data["org_a"].id, status="active", demo_mode=False,
        )
        other.role = data["agent_a"].role
        other.organization = data["org_a"]
        await _as_user(other)
        resp = await api.put(f"/api/v1/admin/knowledge-bases/{kb_id}", json={"name": "改名"})
        assert resp.status_code == 403, resp.text

        # 创建者 update → 200
        await _as_user(data["agent_a"])
        resp = await api.put(f"/api/v1/admin/knowledge-bases/{kb_id}", json={"name": "改名成功"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["name"] == "改名成功"

    # 4. delete cascade
    async def test_delete_cascade(self, session):
        data = await _seed(session)
        repo = KnowledgeBaseRepository(session)
        kb = await repo.create_knowledge_base(
            name="待删除库", organization_id=data["org_a"].id, created_by=data["agent_a"].id,
        )
        await session.flush()
        doc = Document(
            knowledge_base_id=kb.id, title="文档1", file_name="doc1.txt",
            file_type="txt", file_size=10, status="published", chunk_count=1,
        )
        session.add(doc)
        await session.flush()
        session.add(DocumentChunk(
            document_id=doc.id, chunk_index=0, content="内容", token_count=2,
        ))
        await session.commit()

        deleted = await repo.delete_knowledge_base(kb.id)
        await session.commit()
        assert deleted is True
        kb_count = (await session.execute(
            select(func.count()).select_from(KnowledgeBase).where(KnowledgeBase.id == kb.id)
        )).scalar()
        doc_count = (await session.execute(
            select(func.count()).select_from(Document).where(Document.knowledge_base_id == kb.id)
        )).scalar()
        chunk_count = (await session.execute(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )).scalar()
        assert kb_count == 0
        assert doc_count == 0, "FK CASCADE 应级联删除 documents"
        assert chunk_count == 0, "FK CASCADE 应级联删除 document_chunks"

    # 5. organization scope（API 层：AGENT@A 可见，AGENT@B 不可见）
    async def test_organization_scope(self, session, api):
        data = await _seed(session)
        await session.commit()

        async def _as_user(user):
            async def _cu():
                return user
            app.dependency_overrides[get_current_user] = _cu

        # AGENT@A 创建 org A KB
        await _as_user(data["agent_a"])
        resp = await api.post("/api/v1/admin/knowledge-bases", json={
            "name": "A组织专属库", "description": "", "category": "product",
        })
        assert resp.status_code == 200, resp.text
        kb_id = resp.json()["data"]["id"]
        assert resp.json()["data"]["organization_id"] == str(data["org_a"].id)

        # AGENT@A 列表可见
        resp = await api.get("/api/v1/admin/knowledge-bases")
        assert resp.status_code == 200
        names_a = [kb["name"] for kb in resp.json()["data"]]
        assert "A组织专属库" in names_a

        # AGENT@B 列表不可见
        await _as_user(data["agent_b"])
        resp = await api.get("/api/v1/admin/knowledge-bases")
        names_b = [kb["name"] for kb in resp.json()["data"]]
        assert "A组织专属库" not in names_b, "AGENT@B 不应看到 org A KB"

        # AGENT@B 详情 → 404
        resp = await api.get(f"/api/v1/admin/knowledge-bases/{kb_id}")
        assert resp.status_code == 404, resp.text

    # 6. role scope（repo 层过滤）
    async def test_role_scope(self, session):
        data = await _seed(session)
        repo = KnowledgeBaseRepository(session)
        await repo.create_knowledge_base(
            name="代理人专用库", organization_id=data["org_a"].id,
            allowed_roles=["AGENT"], created_by=data["agent_a"].id,
        )
        await session.commit()

        # AGENT 角色可见（allowed_roles 包含）
        records, _ = await repo.list_knowledge_bases(
            user_roles=["AGENT"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        assert "代理人专用库" in {r.name for r in records}

        # HQ_ADMIN 角色不可见（精确角色不匹配，Task 17B §2.3.3 硬约束）
        records, _ = await repo.list_knowledge_bases(
            user_roles=["HQ_ADMIN"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        assert "代理人专用库" not in {r.name for r in records}

    # 7. duplicate name handling
    async def test_duplicate_name(self, session, api):
        data = await _seed(session)
        await session.commit()

        async def _as_user(user):
            async def _cu():
                return user
            app.dependency_overrides[get_current_user] = _cu

        await _as_user(data["agent_a"])
        resp = await api.post("/api/v1/admin/knowledge-bases", json={"name": "同名知识库"})
        assert resp.status_code == 200, resp.text
        resp = await api.post("/api/v1/admin/knowledge-bases", json={"name": "同名知识库"})
        assert resp.status_code == 409, resp.text
        assert resp.json()["detail"]["code"] == "DUPLICATE_NAME"

        # repo.name_exists 直接验证
        repo = KnowledgeBaseRepository(session)
        assert await repo.name_exists("同名知识库", data["org_a"].id) is True
        assert await repo.name_exists("不存在的名字", data["org_a"].id) is False
