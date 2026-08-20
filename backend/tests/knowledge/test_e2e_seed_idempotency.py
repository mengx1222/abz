"""Task 24 — P2-4 E2E seed 幂等性 & fail-fast 验证（backend-pg）。

覆盖目标：
1. seed_e2e_knowledge 首次创建返回 True，二次调用返回 False（不重复插入）——
   seed 可重复执行且不产生重复 KB/文档
2. embedding 失败 → fail-fast（RuntimeError），且不留半成品（未 commit → rollback）——
   杜绝 NULL 向量 chunk 静默污染 pgvector 检索
3. 已存在但计数不一致的 KB → 警告 + 跳过（不静默、不破坏数据）

通过环境变量 AZB_TEST_DATABASE_URL 指定真实 PostgreSQL（含 pgvector），
未设置时整个模块跳过（CI backend-pg job 提供）。
"""
import os

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Base, KnowledgeBase

from scripts.e2e_seed_knowledge import KB_NAME, seed_e2e_knowledge

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
    """conftest 默认 DEMO_MODE=true；seed 逻辑必须走真实生产分支 + mock AI。"""
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")


async def _cleanup_e2e_kb(session: AsyncSession) -> None:
    """清理本测试创建的 E2E KB（避免污染同库其他测试）。"""
    from sqlalchemy import delete

    kb = (
        await session.execute(select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME))
    ).scalars().first()
    if kb is not None:
        await session.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb.id))
        await session.commit()


class TestE2eSeedIdempotency:
    async def test_seed_creates_once_then_skips(self, session: AsyncSession):
        """首次创建返回 True，二次调用返回 False（幂等，不重复插入）。"""
        await _cleanup_e2e_kb(session)

        created_first = await seed_e2e_knowledge(session)
        await session.commit()
        assert created_first is True

        created_second = await seed_e2e_knowledge(session)
        await session.commit()
        assert created_second is False

        # 落库验证：只存在一个 KB，计数与预期一致
        kbs = (
            await session.execute(select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME))
        ).scalars().all()
        assert len(kbs) == 1
        # RDY 阶段1：新增「销售合规与常见异议指南」文档（3 docs / 9 chunks）
        assert kbs[0].document_count == 3
        assert kbs[0].total_chunks == 9

        await _cleanup_e2e_kb(session)

    async def test_seed_embedding_failure_fails_fast(self, session: AsyncSession, monkeypatch):
        """embedding 失败 → RuntimeError 且无半成品残留（未 commit → rollback）。"""
        await _cleanup_e2e_kb(session)

        import app.ai.gateway as gateway_module

        class _FailingGateway:
            async def embed(self, texts):
                raise RuntimeError("embed provider down")

        monkeypatch.setattr(gateway_module, "get_ai_gateway", lambda: _FailingGateway())

        with pytest.raises(RuntimeError, match="embedding failed"):
            await seed_e2e_knowledge(session)
        # 不 commit —— 测试会话关闭自动回滚，无 KB 半成品
        await session.rollback()

        # 用新会话验证 DB 中无残留（旧会话能看到未提交的 flush 数据，不能作为依据）
        factory = async_sessionmaker(session.bind, class_=AsyncSession, expire_on_commit=False)
        async with factory() as fresh:
            kb = (
                await fresh.execute(
                    select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME)
                )
            ).scalars().first()
            assert kb is None

    async def test_seed_skip_on_mismatched_counts_warns(self, session: AsyncSession, capsys):
        """已存在但计数不一致 → 跳过 + 警告（不自动重建）。"""
        from sqlalchemy import delete

        await _cleanup_e2e_kb(session)

        # 造一个计数不一致的假 KB
        fake = KnowledgeBase(
            name=KB_NAME,
            description="mismatch fixture",
            category="product",
            status="active",
            is_public=True,
            document_count=0,
            total_chunks=0,
        )
        session.add(fake)
        await session.commit()

        created = await seed_e2e_knowledge(session)
        await session.commit()
        assert created is False

        captured = capsys.readouterr()
        assert "mismatched counts" in captured.out

        # 数据未被破坏（仍是 0/0 的假 KB）
        kbs = (
            await session.execute(select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME))
        ).scalars().all()
        assert len(kbs) == 1
        assert kbs[0].document_count == 0

        await _cleanup_e2e_kb(session)
