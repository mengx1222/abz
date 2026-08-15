"""Script Service RAG 生产路径测试。

在 DEMO_MODE=false 下直接驱动 ScriptService，验证：
- 生产模式 RAG Pipeline 使用数据库检索器（Retriever，而非 DemoRetriever）
- 话术生成（SSE）在生产模式正常流式输出并持久化到数据库

说明: SQLite 上生产检索器的 pgvector/tsvector 查询会优雅降级为空结果；
真实的 RAG 知识库检索需 PostgreSQL + pgvector（见后续真实环境验收）。
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
from app.rag.retriever import DemoRetriever, Retriever
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


class TestScriptRagProduction:
    async def test_production_pipeline_uses_db_retriever(self, session, monkeypatch):
        await _create_user(session, "13900550001")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        pipeline = await service._get_rag_pipeline()
        assert pipeline is not None
        retriever = await pipeline._get_retriever()
        assert isinstance(retriever, Retriever)
        assert not isinstance(retriever, DemoRetriever)

    async def test_generate_scripts_production_persists(self, session, monkeypatch):
        uid = await _create_user(session, "13900550002")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        events = [
            e async for e in service.generate_scripts(
                customer_context={"name": "张先生", "age": 35, "stage": "needs_analysis"},
                style="professional",
                product_type="医疗险",
                user_id=str(uid),
            )
        ]
        assert any("generation_complete" in e for e in events)

        # 生成的脚本已持久化到数据库（归属当前用户）
        rows = (await session.execute(select(Script))).scalars().all()
        assert len(rows) >= 1
        assert all(str(r.created_by) == str(uid) for r in rows)
        assert all(r.compliance_status in ("green", "yellow", "red") for r in rows)
