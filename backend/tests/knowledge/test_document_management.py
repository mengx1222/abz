"""Task 22 — Document Management Production 集成测试（PostgreSQL + pgvector）。

通过环境变量 AZB_TEST_DATABASE_URL 指定真实 PostgreSQL（含 pgvector），
未设置时整个模块跳过（CI backend-pg job 提供）。

覆盖用例（任务矩阵 7 项）：
1. document list success
2. document detail
3. organization isolation（AGENT@A 可见 / AGENT@B 不可见）
4. role isolation（allowed_roles=["AGENT"]：AGENT 可见 / HQ_ADMIN 不可见）
5. publish status change（publish → published / unpublish → draft）
6. delete cascade（FK CASCADE 级联删 document_chunks/embedding，无孤儿）
7. unauthorized delete（非管理/非创建者 → 403）
"""
import os
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import func, select, text
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
from app.repositories.document_repository import DocumentRepository

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
    """conftest 默认 DEMO_MODE=true；文档管理测试必须走真实生产分支。"""
    monkeypatch.setattr(settings, "DEMO_MODE", False)


async def _get_or_create_role(session: AsyncSession, code: str, name: str) -> Role:
    role = (await session.execute(select(Role).where(Role.code == code))).scalars().first()
    if role is None:
        role = Role(code=code, name=name, level=1)
        session.add(role)
        await session.flush()
    return role


def _rand_phone() -> str:
    return "17" + str(uuid.uuid4().int)[:11]


async def _seed(session: AsyncSession) -> dict:
    """org A/B + 角色 + 用户 + KB（org A, allowed_roles=["AGENT"]）+ 2 文档。"""
    suffix = uuid.uuid4().hex[:6]
    org_a = Organization(name=f"组织A-{suffix}", type=OrgType.BRANCH)
    org_b = Organization(name=f"组织B-{suffix}", type=OrgType.BRANCH)
    session.add_all([org_a, org_b])
    await session.flush()

    role_agent = await _get_or_create_role(session, "AGENT", "代理人")
    role_hq = await _get_or_create_role(session, "HQ_ADMIN", "总部管理员")

    def _user(role: Role, org: Organization) -> User:
        u = User(
            phone=_rand_phone(), name="测试用户", password_hash=None,
            role_id=role.id, organization_id=org.id,
            status="active", demo_mode=False,
        )
        u.role = role
        u.organization = org
        session.add(u)
        return u

    agent_a = _user(role_agent, org_a)
    agent_b = _user(role_agent, org_b)
    hq_a = _user(role_hq, org_a)
    await session.flush()

    kb = KnowledgeBase(
        name=f"文档库-{suffix}", description="文档管理测试",
        category="product", status="active", is_public=True,
        allowed_roles=["AGENT"], organization_id=org_a.id,
    )
    session.add(kb)
    await session.flush()

    repo = DocumentRepository(session)
    doc_pub = await repo.create_document(
        knowledge_base_id=kb.id,
        title="已发布文档",
        file_name="published.md",
        file_type="md",
        content_text="医疗险产品说明",
        status="published",
        created_by=agent_a.id,
    )
    doc_draft = await repo.create_document(
        knowledge_base_id=kb.id,
        title="草稿文档",
        file_name="draft.md",
        file_type="md",
        content_text="草稿内容",
        status="draft",
        created_by=agent_a.id,
    )
    await session.commit()
    return {
        "org_a": org_a, "org_b": org_b,
        "agent_a": agent_a, "agent_b": agent_b, "hq_a": hq_a,
        "kb": kb.id,
        "doc_pub": doc_pub.id, "doc_draft": doc_draft.id,
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


class TestDocumentManagement:
    """任务矩阵 7 用例。"""

    # 1. document list success
    async def test_list_documents_success(self, session):
        data = await _seed(session)
        repo = DocumentRepository(session)
        records, total = await repo.list_documents(
            data["kb"],
            user_roles=["AGENT"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        names = {r.title for r in records}
        assert "已发布文档" in names
        assert "草稿文档" in names
        assert total == 2

        # status 过滤
        records_pub, _ = await repo.list_documents(
            data["kb"], status="published",
            user_roles=["AGENT"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        assert {r.title for r in records_pub} == {"已发布文档"}

    # 2. document detail
    async def test_document_detail(self, session):
        data = await _seed(session)
        repo = DocumentRepository(session)
        doc = await repo.get_document(
            data["doc_pub"], kb_id=data["kb"],
            user_roles=["AGENT"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        assert doc is not None
        assert doc.title == "已发布文档"
        assert doc.file_type == "md"
        assert doc.status == "published"
        assert str(doc.knowledge_base_id) == str(data["kb"])

    # 3. organization isolation（API 层）
    async def test_organization_isolation(self, session, api):
        data = await _seed(session)

        async def _as_user(user):
            async def _cu():
                return user
            app.dependency_overrides[get_current_user] = _cu

        # AGENT@A 可见
        await _as_user(data["agent_a"])
        resp = await api.get(f"/api/v1/admin/knowledge-bases/{data['kb']}/documents")
        assert resp.status_code == 200, resp.text
        titles = [d["title"] for d in resp.json()["data"]]
        assert "已发布文档" in titles
        resp = await api.get(f"/api/v1/admin/knowledge-bases/{data['kb']}/documents/{data['doc_pub']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "已发布文档"

        # AGENT@B 不可见（list 不含 + detail 404）
        await _as_user(data["agent_b"])
        resp = await api.get(f"/api/v1/admin/knowledge-bases/{data['kb']}/documents")
        assert resp.status_code == 200
        assert "已发布文档" not in [d["title"] for d in resp.json()["data"]]
        resp = await api.get(f"/api/v1/admin/knowledge-bases/{data['kb']}/documents/{data['doc_pub']}")
        assert resp.status_code == 404, resp.text

    # 4. role isolation（repo 层）
    async def test_role_isolation(self, session):
        data = await _seed(session)
        repo = DocumentRepository(session)

        # AGENT 可见（KB allowed_roles=["AGENT"] 命中）
        records, _ = await repo.list_documents(
            data["kb"],
            user_roles=["AGENT"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        assert "已发布文档" in {r.title for r in records}

        # HQ_ADMIN 不可见（精确角色不匹配，Task 17B §2.3.3 硬约束）
        records, _ = await repo.list_documents(
            data["kb"],
            user_roles=["HQ_ADMIN"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        assert "已发布文档" not in {r.title for r in records}

        # HQ_ADMIN 直接 get → None（越权）
        doc = await repo.get_document(
            data["doc_pub"], kb_id=data["kb"],
            user_roles=["HQ_ADMIN"],
            accessible_org_ids=[str(data["org_a"].id)],
        )
        assert doc is None

    # 5. publish status change（publish → published / unpublish → draft）
    async def test_publish_status_change(self, session):
        data = await _seed(session)
        repo = DocumentRepository(session)

        # draft 草稿发布
        pub = await repo.publish_document(data["doc_draft"], published_by=data["agent_a"].id)
        assert pub is not None
        assert pub.status == "published"
        assert pub.published_at is not None
        assert pub.published_by == data["agent_a"].id
        await session.commit()

        # 重新查询确认落库
        check = await repo.get_document(
            data["doc_draft"], kb_id=data["kb"],
            user_roles=["AGENT"], accessible_org_ids=[str(data["org_a"].id)],
        )
        assert check is not None and check.status == "published"

        # unpublish → draft
        un = await repo.unpublish_document(data["doc_draft"], updated_by=data["agent_a"].id)
        await session.commit()
        assert un is not None and un.status == "draft"

    # 6. delete cascade（FK CASCADE 删 chunks/embedding，无孤儿）
    async def test_delete_cascade(self, session):
        data = await _seed(session)
        repo = DocumentRepository(session)

        # 给 doc_pub 加 chunk（带 embedding 元数据）
        chunk = DocumentChunk(
            document_id=data["doc_pub"], chunk_index=0,
            content="医疗险产品说明", token_count=10,
            embedding=[0.1] * 1536, search_text="医疗险产品说明",
            metadata_={"document_id": str(data["doc_pub"]), "document_title": "已发布文档"},
        )
        session.add(chunk)
        await session.commit()
        assert (await session.execute(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == data["doc_pub"])
        )).scalar() == 1

        deleted = await repo.delete_document(data["doc_pub"])
        await session.commit()
        assert deleted is True
        doc_count = (await session.execute(
            select(func.count()).select_from(Document).where(Document.id == data["doc_pub"])
        )).scalar()
        chunk_count = (await session.execute(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == data["doc_pub"])
        )).scalar()
        assert doc_count == 0
        assert chunk_count == 0, "FK CASCADE 应级联删除 document_chunks（含 embedding），无孤儿数据"

    # 7. unauthorized delete（非管理/非创建者 → 403）
    async def test_unauthorized_delete(self, session, api):
        data = await _seed(session)

        async def _as_user(user):
            async def _cu():
                return user
            app.dependency_overrides[get_current_user] = _cu

        # 创建者（agent_a）删除 → 200
        await _as_user(data["agent_a"])
        # 先用草稿文档测 403：agent_b 非管理角色且非创建者
        await _as_user(data["agent_b"])
        resp = await api.delete(f"/api/v1/admin/knowledge-bases/{data['kb']}/documents/{data['doc_draft']}")
        assert resp.status_code == 403, resp.text
        # 文档仍在
        await _as_user(data["agent_a"])
        resp = await api.get(f"/api/v1/admin/knowledge-bases/{data['kb']}/documents/{data['doc_draft']}")
        assert resp.status_code == 200

        # 创建者删除 → 200
        resp = await api.delete(f"/api/v1/admin/knowledge-bases/{data['kb']}/documents/{data['doc_draft']}")
        assert resp.status_code == 200, resp.text
        resp = await api.get(f"/api/v1/admin/knowledge-bases/{data['kb']}/documents/{data['doc_draft']}")
        assert resp.status_code == 404
