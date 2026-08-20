"""ULTIMATE P0-2 — 产品问答会话历史生产持久化。

覆盖（真实 PG 集成，backend-pg job 提供 AZB_TEST_DATABASE_URL）：
1. 新会话：_real_chat 落库 user + assistant 消息（finish_reason=stop + sources）
2. 历史注入：同一会话第二次调用，历史注入 LLM messages（mock gateway 捕获）
3. 用户隔离：A 的会话 B 不可见（get_owned None / 列表隔离）
4. KB 拒答：无检索结果 → finish_reason=refused 落库
5. Repository 计数：append_message 后 message_count 递增

无 PG 环境自动跳过（unit job 不含 AZB_TEST_DATABASE_URL）。
"""
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.conversation import Conversation, Message
from app.models.organization import Organization, OrgType
from app.models.role import Role
from app.models.user import User
from app.repositories.conversation_repo import ConversationRepository

PG_URL = os.environ.get("AZB_TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not PG_URL, reason="AZB_TEST_DATABASE_URL not set"),
]

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")


# ------------------------------------------------------------------
# Fakes
# ------------------------------------------------------------------

class FakeResult:
    def __init__(self, title="文档A", score=0.85):
        self.document_title = title
        self.chunk_id = f"chunk-{uuid.uuid4()}"
        self.score = score
        self.metadata = {"heading": "保障范围"}


class FakePipeline:
    """RAG pipeline 替身：可配置返回结果或空。"""

    def __init__(self):
        self.results = [FakeResult()]
        self.context = "合成知识上下文"

    async def query(self, **kwargs):
        return self.results, self.context


class FakeGateway:
    """AI gateway 替身：流式返回固定 token，捕获 messages。"""

    def __init__(self):
        self.captured_messages = None

    async def chat(self, messages=None, **kwargs):
        self.captured_messages = messages
        for tok in ["安", "诊", "保", "测", "试"]:
            yield tok


# ------------------------------------------------------------------
# PG fixtures
# ------------------------------------------------------------------

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


@pytest_asyncio.fixture
async def org_and_role(session: AsyncSession):
    org = Organization(id=ORG_ID, name="测试机构", type=OrgType.HQ)
    session.add(org)
    role = Role(id=ROLE_ID, code="AGENT", name="代理人", level=1)
    session.add(role)
    await session.flush()
    return org, role


@pytest_asyncio.fixture
async def users(session: AsyncSession, org_and_role):
    _, role = org_and_role
    a = User(
        phone="13800001001", name="用户A", password_hash="x", status="active",
        demo_mode=False, role_id=role.id, organization_id=ORG_ID,
    )
    b = User(
        phone="13800001002", name="用户B", password_hash="x", status="active",
        demo_mode=False, role_id=role.id, organization_id=ORG_ID,
    )
    session.add_all([a, b])
    await session.flush()
    return a, b


async def _consume(svc, user, question, conversation_id):
    """消费完整 SSE 流，返回最后 message_complete 事件数据。"""
    import json
    last = {}
    async for event_json in svc.chat(
        user=user, question=question, conversation_id=conversation_id,
    ):
        d = json.loads(event_json)
        if d["event"] == "message_complete":
            last = d["data"]
    return last


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

@pytest.mark.integration
class TestConversationPersistenceProduction:
    async def test_new_conversation_persists_messages(
        self, session: AsyncSession, users
    ):
        """新会话：user + assistant 消息落库（finish_reason=stop + sources）。"""
        a, _ = users
        from app.ai.service import ProductQaService
        svc = ProductQaService(db=session)
        fake_gw = FakeGateway()
        svc.gateway = fake_gw
        svc._pipeline = FakePipeline()

        conv_id = str(uuid.uuid4())
        last = await _consume(svc, a, "百万医疗险保什么", conv_id)
        assert last["finish_reason"] == "stop"
        assert last["sources_count"] == 1

        await session.commit()
        conv = (await session.execute(
            select(Conversation).where(Conversation.id == uuid.UUID(conv_id))
        )).scalars().first()
        assert conv is not None
        assert conv.user_id == str(a.id)
        assert conv.message_count == 2
        msgs = (await session.execute(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
        )).scalars().all()
        assert [m.role for m in msgs] == ["user", "assistant"]
        assert msgs[0].content == "百万医疗险保什么"
        assert msgs[1].finish_reason == "stop"
        assert msgs[1].knowledge_sources and msgs[1].knowledge_sources[0]["chunk_id"]

    async def test_history_injected_on_second_turn(
        self, session: AsyncSession, users
    ):
        """二次调用：历史注入 LLM messages（含上轮 user/assistant）。"""
        a, _ = users
        from app.ai.service import ProductQaService
        svc = ProductQaService(db=session)
        fake_gw = FakeGateway()
        svc.gateway = fake_gw
        svc._pipeline = FakePipeline()

        conv_id = str(uuid.uuid4())
        await _consume(svc, a, "第一轮问题", conv_id)
        await session.commit()

        # 第二轮：历史应注入
        svc2 = ProductQaService(db=session)
        fake_gw2 = FakeGateway()
        svc2.gateway = fake_gw2
        svc2._pipeline = FakePipeline()
        await _consume(svc2, a, "第二轮问题", conv_id)

        roles = [m["role"] for m in fake_gw2.captured_messages]
        contents = [m["content"] for m in fake_gw2.captured_messages]
        assert roles == ["system", "user", "assistant", "user"]
        assert contents[1] == "第一轮问题"
        assert contents[2] == "安诊保测试"  # gateway token 拼接
        assert contents[3] == "第二轮问题"

    async def test_owner_isolation(self, session: AsyncSession, users):
        """用户隔离：A 的会话 B 不可见（get_owned None / 列表仅本人）。"""
        a, b = users
        from app.ai.service import ProductQaService
        svc = ProductQaService(db=session)
        svc.gateway = FakeGateway()
        svc._pipeline = FakePipeline()

        conv_id = str(uuid.uuid4())
        await _consume(svc, a, "我的问题", conv_id)
        await session.commit()

        repo = ConversationRepository(session)
        assert await repo.get_owned(uuid.UUID(conv_id), a.id) is not None
        assert await repo.get_owned(uuid.UUID(conv_id), b.id) is None
        a_list = await repo.list_by_user(a.id)
        b_list = await repo.list_by_user(b.id)
        assert any(c.id == uuid.UUID(conv_id) for c in a_list)
        assert not any(c.id == uuid.UUID(conv_id) for c in b_list)

    async def test_kb_refusal_persisted(self, session: AsyncSession, users):
        """KB 拒答：无检索结果 → finish_reason=refused 落库。"""
        a, _ = users
        from app.ai.service import ProductQaService
        svc = ProductQaService(db=session)
        svc.gateway = FakeGateway()
        empty_pipeline = FakePipeline()
        empty_pipeline.results = []
        empty_pipeline.context = ""
        svc._pipeline = empty_pipeline

        conv_id = str(uuid.uuid4())
        last = await _consume(svc, a, "无关问题", conv_id)
        assert last["finish_reason"] == "refused"

        await session.commit()
        msgs = (await session.execute(
            select(Message).where(Message.conversation_id == uuid.UUID(conv_id)).order_by(Message.created_at)
        )).scalars().all()
        assert len(msgs) == 2
        assert msgs[1].finish_reason == "refused"
        assert "知识库" in msgs[1].content

    async def test_repo_message_count_increments(self, session: AsyncSession, users):
        """Repository：append_message 后 message_count 递增。"""
        a, _ = users
        repo = ConversationRepository(session)
        conv = await repo.create_conversation(a.id, "计数测试")
        assert conv.message_count == 0
        await repo.append_message(conv.id, "user", "hi")
        await repo.append_message(conv.id, "assistant", "hello", finish_reason="stop")
        await session.commit()
        fresh = (await session.execute(
            select(Conversation).where(Conversation.id == conv.id)
        )).scalars().first()
        assert fresh.message_count == 2
