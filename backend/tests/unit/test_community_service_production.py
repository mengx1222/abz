"""Community Service AI Summary Production 路径测试。

在 DEMO_MODE=false 下直接驱动 CommunityService，使用 SQLite 内存库
(Base.metadata.create_all) 验证生产 AI Summary：
- 正常生成：流式 token + summary 持久化 + summary_complete
- post not found / 已删除帖子 → error
- AI provider failure / timeout / empty result → error，不保存错误文本
- 失败后不写数据库、旧摘要不被覆盖
- SSE: error 后不发 summary_complete

真实 wiring 验证：CommunityService → PostRepository → AI Gateway（最底层 Provider 可 Mock）。
说明: 当前环境无真实 PostgreSQL，使用 SQLite 完成接近 Production 的验证；
真实 PostgreSQL + pgvector 验收由 CI backend-pg job 覆盖。
"""
import json
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
from app.models import Base, Post, User
from app.services.community_service import CommunityService

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


async def _create_post(session: AsyncSession, author_id: uuid.UUID, *, title="测试帖", content="正文内容") -> uuid.UUID:
    post = Post(title=title, content=content, category="experience", author_id=author_id)
    session.add(post)
    await session.flush()
    return post.id


async def _make_production_service(session: AsyncSession, monkeypatch) -> CommunityService:
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    return CommunityService(session=session)


async def _collect_events(service: CommunityService, post_id: str) -> list[dict]:
    events = []
    async for raw in service.generate_ai_summary(post_id):
        events.append(json.loads(raw))
    return events


class TestAiSummaryProduction:
    async def test_generate_success_persists(self, session, monkeypatch):
        """正常生成：流式 token + 持久化 + summary_complete。"""
        author = await _create_user(session, "13900770001")
        pid = await _create_post(session, author, title="如何快速了解客户需求", content="经过实践总结了三个问题……")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        async def _fake_chat(messages, stream=True, **kwargs):
            async def _gen():
                for ch in ["本文介绍了", "三个问题", "了解客户需求的方法。"]:
                    yield ch
            return _gen()

        monkeypatch.setattr(service.gateway, "chat", _fake_chat)

        events = await _collect_events(service, str(pid))
        kinds = [e["event"] for e in events]
        assert "summary_start" in kinds
        assert kinds.count("token") == 3
        assert "summary_complete" in kinds
        assert "error" not in kinds

        # 摘要已持久化
        row = (await session.execute(select(Post).where(Post.id == pid))).scalar_one()
        assert row.ai_summary == "本文介绍了三个问题了解客户需求的方法。"

    async def test_post_not_found(self, session, monkeypatch):
        """post_id 不存在 → error。"""
        await _create_user(session, "13900770002")
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        events = await _collect_events(service, str(uuid.uuid4()))
        assert events[0]["event"] == "error"
        assert events[0]["data"]["message"] == "帖子不存在"

    async def test_deleted_post_refuses(self, session, monkeypatch):
        """已删除帖子 → error（资源边界）。"""
        author = await _create_user(session, "13900770003")
        pid = await _create_post(session, author)
        await session.commit()
        row = (await session.execute(select(Post).where(Post.id == pid))).scalar_one()
        row.is_deleted = True
        await session.commit()

        service = await _make_production_service(session, monkeypatch)
        events = await _collect_events(service, str(pid))
        assert events[0]["event"] == "error"
        assert events[0]["data"]["message"] == "帖子不存在"

    async def test_ai_failure_not_persisted(self, session, monkeypatch):
        """AI 异常：发 error、不写库、不发 summary_complete。"""
        author = await _create_user(session, "13900770004")
        pid = await _create_post(session, author)
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        async def _boom(*args, **kwargs):
            raise RuntimeError("provider connection error")

        monkeypatch.setattr(service.gateway, "chat", _boom)

        events = await _collect_events(service, str(pid))
        kinds = [e["event"] for e in events]
        assert "error" in kinds
        assert "summary_complete" not in kinds
        assert kinds.count("token") == 0

        # 数据库未被写入错误文本
        row = (await session.execute(select(Post).where(Post.id == pid))).scalar_one()
        assert row.ai_summary is None

    async def test_ai_timeout_treated_as_failure(self, session, monkeypatch):
        """AI 超时：与失败同等处理。"""
        author = await _create_user(session, "13900770005")
        pid = await _create_post(session, author)
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        async def _timeout(*args, **kwargs):
            raise TimeoutError("AI gateway timeout")

        monkeypatch.setattr(service.gateway, "chat", _timeout)

        events = await _collect_events(service, str(pid))
        kinds = [e["event"] for e in events]
        assert "error" in kinds
        assert "summary_complete" not in kinds
        row = (await session.execute(select(Post).where(Post.id == pid))).scalar_one()
        assert row.ai_summary is None

    async def test_empty_ai_result_not_persisted(self, session, monkeypatch):
        """空结果：发 error、不写库、不发 summary_complete。"""
        author = await _create_user(session, "13900770006")
        pid = await _create_post(session, author)
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        async def _empty_chat(messages, stream=True, **kwargs):
            async def _gen():
                return
                yield  # pragma: no cover
            return _gen()

        monkeypatch.setattr(service.gateway, "chat", _empty_chat)

        events = await _collect_events(service, str(pid))
        kinds = [e["event"] for e in events]
        assert "error" in kinds
        assert "summary_complete" not in kinds
        row = (await session.execute(select(Post).where(Post.id == pid))).scalar_one()
        assert row.ai_summary is None

    async def test_old_summary_not_overwritten_on_failure(self, session, monkeypatch):
        """旧摘要存在时失败：保持旧摘要不被错误覆盖。"""
        author = await _create_user(session, "13900770007")
        pid = await _create_post(session, author)
        row = (await session.execute(select(Post).where(Post.id == pid))).scalar_one()
        row.ai_summary = "旧的正常摘要"
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        async def _boom(*args, **kwargs):
            raise RuntimeError("provider down")

        monkeypatch.setattr(service.gateway, "chat", _boom)

        events = await _collect_events(service, str(pid))
        assert any(e["event"] == "error" for e in events)
        assert all(e["event"] != "summary_complete" for e in events)

        row = (await session.execute(select(Post).where(Post.id == pid))).scalar_one()
        assert row.ai_summary == "旧的正常摘要"

    async def test_error_then_no_summary_complete(self, session, monkeypatch):
        """SSE 完整性：error 后绝不发送 summary_complete。"""
        author = await _create_user(session, "13900770008")
        pid = await _create_post(session, author)
        await session.commit()
        service = await _make_production_service(session, monkeypatch)

        async def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(service.gateway, "chat", _boom)

        events = await _collect_events(service, str(pid))
        # 事件序列以 error 终止，没有 summary_complete
        assert events[-1]["event"] == "error"
        assert "summary_complete" not in [e["event"] for e in events]

    async def test_real_wiring_service_to_repo_to_gateway(self, session, monkeypatch):
        """验证真实 Service → PostRepository → AI Gateway wiring（底层 Provider Mock）。"""
        author = await _create_user(session, "13900770009")
        pid = await _create_post(session, author, title="真实链路验证")
        await session.commit()

        # 只 Mock 最底层 gateway.chat，Service/Repository/持久化全部真实
        service = await _make_production_service(session, monkeypatch)
        called_messages = []

        async def _fake_chat(messages, stream=True, **kwargs):
            called_messages.append(messages)
            async def _gen():
                yield "真实摘要"
            return _gen()

        monkeypatch.setattr(service.gateway, "chat", _fake_chat)

        events = await _collect_events(service, str(pid))
        assert any(e["event"] == "summary_complete" for e in events)

        # 传给 AI 的只有 title + content（无手机号/ID 等敏感字段）
        assert len(called_messages) == 1
        user_payload = called_messages[0][-1]["content"]
        assert "标题：真实链路验证" in user_payload
        assert "正文内容" in user_payload
        assert "13900770009" not in user_payload

        # 持久化真实摘要
        row = (await session.execute(select(Post).where(Post.id == pid))).scalar_one()
        assert row.ai_summary == "真实摘要"
