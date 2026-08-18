"""Task 20 — Knowledge Production Ingestion（PostgreSQL + pgvector）集成测试。

通过 AZB_TEST_DATABASE_URL 指定真实 PostgreSQL（含 pgvector），未设置时整模块跳过
（CI backend-pg job 提供）。

覆盖：
- 文档创建 / 解析 / chunk 持久化 / embedding 持久化 / metadata 持久化
- organization scope + allowed_roles 权限边界（新导入文档）
- 事务 rollback（embedding 失败 / 空文档不留残留）
- 重复索引幂等（同 document_id 重建，计数不重复累加）
- RAG end-to-end：新文档 → PG/pgvector → Retriever 命中 → SearchResult(document_title)
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.ai.protocol import EmbedResponse
from app.core.config import settings
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
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever

PG_URL = os.environ.get("AZB_TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not PG_URL, reason="AZB_TEST_DATABASE_URL not set"),
]

DIM = 1536

# 确定性向量模式：与 query 向量一致 → 余弦距离最小
VEC_PATTERN = [0.1 if j % 2 == 0 else 0.2 for j in range(DIM)]


class FakeEmbedGateway:
    """模拟 AIGateway 输出（确定性 1536 维），验证 pipeline 经 gateway 而非绑定 SDK。"""

    async def embed(self, texts, model=None, **kwargs) -> EmbedResponse:
        return EmbedResponse(
            embeddings=[list(VEC_PATTERN) for _ in texts],
            model="fake-embed",
            prompt_tokens=0,
            latency_ms=1,
        )


class FailingEmbedGateway:
    """embedding 失败模拟（验证事务回滚）。"""

    async def embed(self, texts, model=None, **kwargs) -> EmbedResponse:
        raise RuntimeError("embedding provider timeout")


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


async def _get_or_create_role(session, code: str, name: str) -> Role:
    role = (await session.execute(select(Role).where(Role.code == code))).scalars().first()
    if role is None:
        role = Role(code=code, name=name, level=1)
        session.add(role)
        await session.flush()
    return role


async def _seed_kb(session) -> dict:
    """清理共享 KB + 创建 org A/B、角色、KB-A（allowed_roles=[AGENT], org=A）。"""
    await session.execute(delete(KnowledgeBase).where(KnowledgeBase.organization_id.is_(None)))
    await session.flush()

    suffix = uuid.uuid4().hex[:6]
    org_a = Organization(name=f"OrgA-{suffix}", type=OrgType.BRANCH)
    org_b = Organization(name=f"OrgB-{suffix}", type=OrgType.BRANCH)
    session.add_all([org_a, org_b])
    await session.flush()

    role_agent = await _get_or_create_role(session, "AGENT", "代理人")
    role_hq = await _get_or_create_role(session, "HQ_ADMIN", "总部管理员")

    def _user(phone: str, role, org) -> User:
        u = User(
            phone=phone, name=f"用户{phone[-4:]}", password_hash=None,
            role_id=role.id, organization_id=org.id,
            status="active", demo_mode=False,
        )
        session.add(u)
        return u

    agent_a = _user(f"1390088{suffix[:4]}01", role_agent, org_a)
    hq_a = _user(f"1390088{suffix[:4]}02", role_hq, org_a)
    agent_b = _user(f"1390088{suffix[:4]}03", role_agent, org_b)
    await session.flush()

    kb = KnowledgeBase(
        name=f"KB-{suffix}", description="ingestion test",
        category="product", status="active", is_public=True,
        allowed_roles=["AGENT"], organization_id=org_a.id,
    )
    session.add(kb)
    await session.flush()
    return {
        "kb": kb.id, "org_a": org_a.id, "org_b": org_b.id,
        "agent_a": agent_a, "hq_a": hq_a, "agent_b": agent_b,
    }


def _make_pipeline(session, gateway) -> RAGPipeline:
    p = RAGPipeline(db=session)
    p.gateway = gateway  # 替换 AIGateway（复用 provider 契约，不绑定 SDK）
    return p


def _content() -> str:
    return (
        "# 安诊保百万医疗险产品手册\n\n"
        "## 保障范围\n"
        "本产品保障住院医疗、门诊医疗，免赔额 1 万元，等待期 30 天。\n\n"
        "## 理赔流程\n"
        "出险后 10 日内报案，提交理赔资料，审核通过后 5 个工作日内赔付。\n"
    )


async def _count(session, model, **filters) -> int:
    stmt = select(func.count()).select_from(model)
    for k, v in filters.items():
        col = getattr(model, k)
        stmt = stmt.where(col == v)
    return (await session.execute(stmt)).scalar_one()


class TestProductionIngestion:
    @pytest_asyncio.fixture(autouse=True)
    async def _production_mode(self, monkeypatch):
        """conftest 默认 DEMO_MODE=true；ingestion 测试必须走真实生产分支。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)

    async def test_index_persists_document_and_chunks(self, session):
        """文档创建 + 解析 + chunk + embedding + metadata 全部持久化。"""
        data = await _seed_kb(session)
        pipeline = _make_pipeline(session, FakeEmbedGateway())
        doc_id = str(uuid.uuid4())

        result = await pipeline.index_document(
            content=_content(), file_type="md", title="百万医疗险产品手册",
            file_name="百万医疗险产品手册.md",
            knowledge_base_id=str(data["kb"]), document_id=doc_id,
            product_type="医疗险",
        )
        assert result["chunks_count"] >= 1
        assert result["document_id"] == doc_id

        doc = (await session.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))).scalar_one()
        assert doc.status == "published"
        assert doc.chunk_count == result["chunks_count"]
        assert doc.content_text and "保障范围" in doc.content_text
        assert doc.published_at is not None
        assert doc.metadata_["product_type"] == "医疗险"
        assert doc.metadata_["organization_id"] == str(data["org_a"])
        assert doc.metadata_["allowed_roles"] == ["AGENT"]

        chunks = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(doc_id))
        )).scalars().all()
        assert len(chunks) == result["chunks_count"]
        for c in chunks:
            assert c.embedding is not None and len(c.embedding) == DIM
            assert c.search_text and len(c.search_text) > 0
            m = c.metadata_
            assert m["document_id"] == doc_id
            assert m["document_title"] == "百万医疗险产品手册"
            assert m["product_type"] == "医疗险"
            assert m["organization_id"] == str(data["org_a"])
            assert m["allowed_roles"] == ["AGENT"]
            assert m["version"] == 1
            assert m["status"] == "published"
            assert m["section"]  # heading 非空

    async def test_index_embeds_via_gateway(self, session):
        """embedding 由 AIGateway 产出并持久化（与 pgvector 1536 维一致）。"""
        data = await _seed_kb(session)
        pipeline = _make_pipeline(session, FakeEmbedGateway())
        doc_id = str(uuid.uuid4())
        await pipeline.index_document(
            content=_content(), file_type="md", title="嵌入验证",
            file_name="嵌入验证.md", knowledge_base_id=str(data["kb"]),
            document_id=doc_id,
        )
        chunks = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(doc_id))
        )).scalars().all()
        assert len(chunks) >= 1
        # pgvector 以 float4 存储 → 与 gateway 输出近似相等（abs=1e-3）
        for c in chunks:
            assert len(c.embedding) == DIM
            assert c.embedding == pytest.approx(list(VEC_PATTERN), abs=1e-3)

    async def test_new_document_retrievable_after_index(self, session):
        """新导入文档 → PG/pgvector → Retriever 命中 → SearchResult（citation 基础）。"""
        data = await _seed_kb(session)
        pipeline = _make_pipeline(session, FakeEmbedGateway())
        doc_id = str(uuid.uuid4())
        await pipeline.index_document(
            content=_content(), file_type="md", title="百万医疗险产品手册",
            file_name="百万医疗险产品手册.md",
            knowledge_base_id=str(data["kb"]), document_id=doc_id,
            product_type="医疗险",
        )

        retriever = Retriever(db_session=session)
        hits = await retriever.search(
            query="保障范围 免赔额", query_embedding=list(VEC_PATTERN), top_k=5,
            user_roles=["AGENT"], accessible_org_ids=[str(data["org_a"])],
        )
        assert len(hits) >= 1
        hit = hits[0]
        assert "百万医疗险" in hit.document_title
        assert "免赔额" in hit.content or "保障范围" in hit.content

        # pipeline.query → context 包含新知识（RAG 上下文）
        results, context = await pipeline.query(
            "保障范围 免赔额", top_k=5,
            user_roles=["AGENT"], accessible_org_ids=[str(data["org_a"])],
        )
        assert any("百万医疗险" in r.document_title for r in results)
        assert "免赔额" in context or "保障范围" in context

    async def test_permission_scope_on_new_document(self, session):
        """新文档权限：AGENT@A 可访问；HQ_ADMIN（角色不符）与 AGENT@B（组织不符）不可访问。"""
        data = await _seed_kb(session)
        pipeline = _make_pipeline(session, FakeEmbedGateway())
        await pipeline.index_document(
            content=_content(), file_type="md", title="百万医疗险产品手册",
            file_name="手册.md", knowledge_base_id=str(data["kb"]),
            product_type="医疗险",
        )

        retriever = Retriever(db_session=session)
        # AGENT@A → 命中（allowed_roles 含 AGENT，org 匹配）
        hits = await retriever.search(
            query="保障范围", query_embedding=list(VEC_PATTERN), top_k=5,
            user_roles=["AGENT"], accessible_org_ids=[str(data["org_a"])],
        )
        assert len(hits) >= 1
        # HQ_ADMIN@A → allowed_roles=["AGENT"] 精确匹配 → 角色拒绝
        hits_hq = await retriever.search(
            query="保障范围", query_embedding=list(VEC_PATTERN), top_k=5,
            user_roles=["HQ_ADMIN"], accessible_org_ids=[str(data["org_a"])],
        )
        assert hits_hq == []
        # AGENT@B → org 范围拒绝
        hits_b = await retriever.search(
            query="保障范围", query_embedding=list(VEC_PATTERN), top_k=5,
            user_roles=["AGENT"], accessible_org_ids=[str(data["org_b"])],
        )
        assert hits_b == []

    async def test_rollback_on_embedding_failure(self, session):
        """embedding 失败 → 事务回滚，不残留 document/chunks。"""
        data = await _seed_kb(session)
        before_docs = await _count(session, Document)
        before_chunks = await _count(session, DocumentChunk)

        pipeline = _make_pipeline(session, FailingEmbedGateway())
        with pytest.raises(RuntimeError, match="embedding provider timeout"):
            await pipeline.index_document(
                content=_content(), file_type="md", title="失败文档",
                file_name="失败.md", knowledge_base_id=str(data["kb"]),
            )
        assert await _count(session, Document) == before_docs, "embedding 失败后不得残留 document"
        assert await _count(session, DocumentChunk) == before_chunks, "embedding 失败后不得残留 chunks"

    async def test_empty_document_rejected(self, session):
        """空文档 → ValueError，无残留。"""
        data = await _seed_kb(session)
        before_docs = await _count(session, Document)

        pipeline = _make_pipeline(session, FakeEmbedGateway())
        with pytest.raises(ValueError, match="empty"):
            await pipeline.index_document(
                content="   \n  ", file_type="txt", title="空文档",
                file_name="empty.txt", knowledge_base_id=str(data["kb"]),
            )
        assert await _count(session, Document) == before_docs

    async def test_duplicate_index_is_idempotent(self, session):
        """同 document_id 重复索引 → chunks 重建替换、Document 仅 1 条、KB 计数不重复累加。"""
        data = await _seed_kb(session)
        pipeline = _make_pipeline(session, FakeEmbedGateway())
        doc_id = str(uuid.uuid4())

        await pipeline.index_document(
            content=_content(), file_type="md", title="幂等文档",
            file_name="idempotent.md", knowledge_base_id=str(data["kb"]),
            document_id=doc_id, product_type="医疗险",
        )
        first_chunks = await _count(session, DocumentChunk, document_id=uuid.UUID(doc_id))

        await pipeline.index_document(
            content=_content(), file_type="md", title="幂等文档",
            file_name="idempotent.md", knowledge_base_id=str(data["kb"]),
            document_id=doc_id, product_type="医疗险",
        )
        second_chunks = await _count(session, DocumentChunk, document_id=uuid.UUID(doc_id))

        assert second_chunks == first_chunks, "重复索引应重建等价 chunks（不翻倍）"
        assert await _count(session, Document, id=uuid.UUID(doc_id)) == 1

        kb = (await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == data["kb"]))).scalar_one()
        assert kb.document_count == 1, "重复索引不得重复累加文档计数"
        assert kb.total_chunks == first_chunks, "total_chunks 应与实际 chunk 数一致"

    async def test_product_type_metadata_and_filter(self, session):
        """product_type metadata 持久化 + 检索产品边界过滤（错误产品不召回）。"""
        data = await _seed_kb(session)
        pipeline = _make_pipeline(session, FakeEmbedGateway())
        await pipeline.index_document(
            content=_content(), file_type="md", title="百万医疗险产品手册",
            file_name="手册.md", knowledge_base_id=str(data["kb"]),
            product_type="医疗险",
        )

        retriever = Retriever(db_session=session)
        hits = await retriever.search(
            query="保障范围", query_embedding=list(VEC_PATTERN), top_k=5,
            user_roles=["AGENT"], accessible_org_ids=[str(data["org_a"])],
            product_type="医疗险",
        )
        assert len(hits) >= 1, "正确产品应命中"
        hits_wrong = await retriever.search(
            query="保障范围", query_embedding=list(VEC_PATTERN), top_k=5,
            user_roles=["AGENT"], accessible_org_ids=[str(data["org_a"])],
            product_type="车险",
        )
        assert hits_wrong == [], "错误产品不得召回（产品边界）"
