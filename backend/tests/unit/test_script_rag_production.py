"""Script Service RAG + Production 生成路径测试。

在 DEMO_MODE=false 下直接驱动 ScriptService，验证：
- 生产模式 RAG Pipeline 使用数据库检索器（Retriever，而非 DemoRetriever）
- RAG 命中（高置信度）→ 正常生成 + Citation 返回 + 持久化
- RAG 未命中 / 低置信度 → 拒答（style_refused，不生成产品事实话术，不持久化）
- AI Provider 失败 → style_error（不伪造结果）
- Compliance GREEN/YELLOW/RED 进入生成链
- 权限：生成的话术归属当前用户

说明:
- SQLite 上生产检索器的 pgvector/tsvector 查询会优雅降级为空结果，
  因此 RAG 命中场景通过 mock 最底层检索器返回构造的 SearchResult；
  真实 Service → AI Gateway → Compliance wiring 保持不变（任务允许 Mock 最底层）。
- 真实 RAG 检索（pgvector + BM25）由 CI 的 PostgreSQL + pgvector 环境覆盖。
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
from app.models import Base, Script, User
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import DemoRetriever, Retriever, SearchResult
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


def _fake_result(content: str, score: float, title: str = "百万医疗险产品手册") -> SearchResult:
    """构造一个高置信度检索结果。"""
    return SearchResult(
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        document_title=title,
        knowledge_base_id=str(uuid.uuid4()),
        content=content,
        score=score,
        metadata={"heading": "保障范围", "document_title": title},
    )


class _FakePipeline:
    """假 RAG Pipeline：可控返回检索结果，用于验证 ScriptService → RAG 调用链。"""

    def __init__(self, results: list[SearchResult]):
        self._results = results
        self.query_called = False
        self.last_product_type: str | None = None

    async def query(self, question: str, top_k: int = 4, product_type: str | None = None):
        self.query_called = True
        self.last_product_type = product_type
        context = "\n---\n".join(r.content for r in self._results)
        return self._results, context


async def _install_fake_pipeline(service: ScriptService, results: list[SearchResult]) -> _FakePipeline:
    fake = _FakePipeline(results)
    service._rag_pipeline = fake  # type: ignore[assignment]
    return fake


async def _collect_generation(service, *, customer_context=None, style="professional", product_type="医疗险", user_id=None):
    """收集全部 SSE 事件并解析为列表。"""
    events = []
    async for raw in service.generate_scripts(
        customer_context=customer_context or {"name": "张先生", "age": 35, "stage": "needs_analysis"},
        style=style,
        product_type=product_type,
        user_id=user_id,
    ):
        events.append(_parse_event(raw))
    return events


def _parse_event(raw: str) -> dict:
    import json
    return json.loads(raw)


def _events_by_type(events: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for e in events:
        grouped.setdefault(e["event"], []).append(e["data"])
    return grouped


class TestScriptRagProduction:
    async def test_production_pipeline_uses_db_retriever(self, session, monkeypatch):
        await _create_user(session, "13900550001")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        pipeline = await service._get_rag_pipeline()
        assert pipeline is not None
        assert isinstance(pipeline, RAGPipeline)
        retriever = await pipeline._get_retriever()
        assert isinstance(retriever, Retriever)
        assert not isinstance(retriever, DemoRetriever)

    # ------------------------------------------------------------------
    # RAG 命中 → 正常生成 + Citation + 持久化
    # ------------------------------------------------------------------

    async def test_rag_hit_generates_with_citation(self, session, monkeypatch):
        uid = await _create_user(session, "13900550002")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        fake = await _install_fake_pipeline(service, [
            _fake_result("百万医疗险保障额度最高 600 万，免赔额 1 万元/年。", 0.85),
            _fake_result("住院医疗、特殊门诊、门诊手术均在保障范围内。", 0.82),
            _fake_result("0-65 周岁可投保，保费随年龄递增。", 0.78),
        ])

        events = await _collect_generation(service, user_id=str(uid))
        grouped = _events_by_type(events)

        assert fake.query_called, "ScriptService 必须调用 RAG Pipeline 检索"
        # rag_context 带 citations + ALLOW
        rag_ctx = grouped["rag_context"][0]
        assert rag_ctx["status"] == "ALLOW"
        assert rag_ctx["confidence"] == "HIGH"
        assert len(rag_ctx["citations"]) == 3
        assert rag_ctx["citations"][0]["document_title"] == "百万医疗险产品手册"
        # style_complete 带 citations
        complete = grouped["style_complete"][0]
        assert len(complete["citations"]) == 3
        assert "generation_complete" in grouped
        assert grouped["generation_complete"][0]["refused_styles"] == 0

        # 持久化到数据库（归属当前用户）
        rows = (await session.execute(select(Script))).scalars().all()
        assert len(rows) == 1
        assert str(rows[0].created_by) == str(uid)

    # ------------------------------------------------------------------
    # RAG 未命中 → 拒答，不生成产品事实话术
    # ------------------------------------------------------------------

    async def test_rag_no_result_refuses(self, session, monkeypatch):
        uid = await _create_user(session, "13900550003")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        await _install_fake_pipeline(service, [])

        events = await _collect_generation(service, user_id=str(uid))
        grouped = _events_by_type(events)

        rag_ctx = grouped["rag_context"][0]
        assert rag_ctx["status"] == "REFUSE"
        assert rag_ctx["citations"] == []
        # 每个 style 拒答，不生成内容
        assert len(grouped["style_refused"]) == 1
        assert "style_complete" not in grouped
        assert grouped["generation_complete"][0]["refused_styles"] == 1
        # 不持久化伪造话术
        rows = (await session.execute(select(Script))).scalars().all()
        assert rows == []

    async def test_rag_low_confidence_refuses(self, session, monkeypatch):
        uid = await _create_user(session, "13900550004")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        await _install_fake_pipeline(service, [
            _fake_result("低相关性的边缘内容。", 0.2),
        ])

        events = await _collect_generation(service, user_id=str(uid))
        grouped = _events_by_type(events)
        assert grouped["rag_context"][0]["status"] == "REFUSE"
        assert "style_complete" not in grouped
        assert "style_refused" in grouped

    # ------------------------------------------------------------------
    # RAG REVIEW（中等置信度）→ 仍生成但标记 REVIEW
    # ------------------------------------------------------------------

    async def test_rag_review_generates_with_flag(self, session, monkeypatch):
        uid = await _create_user(session, "13900550005")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        await _install_fake_pipeline(service, [
            _fake_result("医疗险保障范围相关内容。", 0.5),
            _fake_result("保费与投保年龄相关。", 0.45),
        ])

        events = await _collect_generation(service, user_id=str(uid))
        grouped = _events_by_type(events)
        assert grouped["rag_context"][0]["status"] == "REVIEW"
        complete = grouped["style_complete"][0]
        assert complete["rag_status"] == "REVIEW"

    # ------------------------------------------------------------------
    # AI Provider 失败 → 明确错误，不伪造结果
    # ------------------------------------------------------------------

    async def test_ai_provider_failure_returns_error(self, session, monkeypatch):
        uid = await _create_user(session, "13900550006")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        await _install_fake_pipeline(service, [
            _fake_result("医疗险保障额度最高 600 万。", 0.85),
            _fake_result("住院医疗在保障范围内。", 0.82),
            _fake_result("0-65 周岁可投保。", 0.78),
        ])

        async def _boom(*args, **kwargs):
            raise RuntimeError("AI provider timeout")

        monkeypatch.setattr(service.gateway, "chat", _boom)

        events = await _collect_generation(service, user_id=str(uid))
        grouped = _events_by_type(events)
        assert "style_error" in grouped
        assert "style_complete" not in grouped
        # 不持久化错误文本
        rows = (await session.execute(select(Script))).scalars().all()
        assert rows == []

    # ------------------------------------------------------------------
    # Compliance 进入生成链（GREEN/YELLOW/RED）
    # ------------------------------------------------------------------

    async def test_compliance_flows_into_generation(self, session, monkeypatch):
        uid = await _create_user(session, "13900550007")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        await _install_fake_pipeline(service, [
            _fake_result("医疗险保障额度最高 600 万。", 0.85),
            _fake_result("住院医疗在保障范围内。", 0.82),
            _fake_result("0-65 周岁可投保。", 0.78),
        ])

        async def _fake_chat(messages, stream=True, **kwargs):
            async def _gen():
                yield "这款产品绝对最好，保证收益稳赚不赔。"
            return _gen()

        monkeypatch.setattr(service.gateway, "chat", _fake_chat)

        events = await _collect_generation(service, user_id=str(uid))
        grouped = _events_by_type(events)
        complete = grouped["style_complete"][0]
        assert complete["compliance"]["status"] == "RED"  # 绝对化 + 收益承诺
        assert complete["compliance"]["score"] <= 60

    # ------------------------------------------------------------------
    # 权限：生成话术归属当前用户（跨用户隔离）
    # ------------------------------------------------------------------

    async def test_generation_scoped_to_user(self, session, monkeypatch):
        alice = await _create_user(session, "13900550008")
        bob = await _create_user(session, "13900550009")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        await _install_fake_pipeline(service, [
            _fake_result("医疗险保障额度最高 600 万。", 0.85),
            _fake_result("住院医疗在保障范围内。", 0.82),
            _fake_result("0-65 周岁可投保。", 0.78),
        ])

        await _collect_generation(service, user_id=str(alice))
        rows = (await session.execute(select(Script))).scalars().all()
        assert len(rows) == 1
        assert str(rows[0].created_by) == str(alice)
        assert str(rows[0].created_by) != str(bob)

    # ------------------------------------------------------------------
    # 无 product_type → 通用话术（不经过 RAG 依据判断，直接生成）
    # ------------------------------------------------------------------

    async def test_generate_without_product_type(self, session, monkeypatch):
        uid = await _create_user(session, "13900550010")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        events = await _collect_generation(service, product_type=None, user_id=str(uid))
        grouped = _events_by_type(events)
        # 无 product_type 时不做 RAG 拒答，直接生成
        assert "style_complete" in grouped
        assert "generation_complete" in grouped

    # ------------------------------------------------------------------
    # 产品边界：正确产品 → ALLOW + Citation；错误产品 → REFUSE
    # ------------------------------------------------------------------

    async def test_product_boundary_passed_to_pipeline(self, session, monkeypatch):
        """ScriptService 必须把 product_type 传给 pipeline.query（产品边界过滤）。"""
        uid = await _create_user(session, "13900550011")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        fake = await _install_fake_pipeline(service, [
            _fake_result("医疗险保障额度最高 600 万。", 0.85),
            _fake_result("住院医疗在保障范围内。", 0.82),
            _fake_result("0-65 周岁可投保。", 0.78),
        ])

        await _collect_generation(service, product_type="医疗险", user_id=str(uid))
        assert fake.last_product_type == "医疗险"

    async def test_wrong_product_no_evidence_refuses(self, session, monkeypatch):
        """错误产品（知识库无对应文档）→ pipeline 返回空 → REFUSE 不生成话术。"""
        uid = await _create_user(session, "13900550012")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        fake = await _install_fake_pipeline(service, [])

        events = await _collect_generation(service, product_type="车险", user_id=str(uid))
        grouped = _events_by_type(events)

        assert fake.last_product_type == "车险"
        rag_ctx = grouped["rag_context"][0]
        assert rag_ctx["status"] == "REFUSE"
        assert rag_ctx["citations"] == []
        assert "style_complete" not in grouped
        assert len(grouped["style_refused"]) == 1
        # 不持久化伪造话术
        rows = (await session.execute(select(Script))).scalars().all()
        assert rows == []

    async def test_correct_product_citation_carried(self, session, monkeypatch):
        """正确产品生成时，style_complete 必须携带 citations（前端 Citation UI 数据源）。"""
        uid = await _create_user(session, "13900550013")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)
        await _install_fake_pipeline(service, [
            _fake_result("医疗险保障额度最高 600 万。", 0.85),
            _fake_result("住院医疗在保障范围内。", 0.82),
            _fake_result("0-65 周岁可投保。", 0.78),
        ])

        events = await _collect_generation(service, product_type="医疗险", user_id=str(uid))
        grouped = _events_by_type(events)
        complete = grouped["style_complete"][0]
        assert complete["rag_status"] == "ALLOW"
        assert len(complete["citations"]) >= 1
        c = complete["citations"][0]
        # Citation UI 所需字段：文档标题 / 章节 / 来源 / 分数
        assert c["document_title"]
        assert "section" in c
        assert c["source"]
        assert "score" in c
