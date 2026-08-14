import json
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.ai.gateway import get_ai_gateway
from app.core.config import settings
from app.models.user import User

logger = get_logger()

# 演示模式的系统提示词
_DEMO_SYSTEM_PROMPT = """你是「安诊保 AI 副驾」，华安保险的智能保险产品专家助手。

你的职责：
1. 帮助保险销售人员快速了解华安保险的产品信息
2. 根据客户需求推荐合适的保险产品组合
3. 解答保险产品的保障范围、保费、理赔等问题
4. 提供专业的保险销售话术和沟通建议

注意事项：
- 回答必须基于华安保险的产品知识
- 所有回复请标注 [Demo/演示] 前缀
- 语言简洁专业，适合保险销售场景
- 如不确定某产品细节，诚实说明并建议咨询产品部门"""


# 演示模式参考来源
_DEMO_SOURCES = [
    {
        "title": "华安百万医疗险产品条款",
        "chunk_id": "demo-chunk-001",
        "relevance_score": 0.95,
    },
    {
        "title": "华安重疾险产品手册",
        "chunk_id": "demo-chunk-002",
        "relevance_score": 0.88,
    },
]


class ProductQaService:
    """产品问答服务 —— 编排 RAG + LLM。"""

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.gateway = get_ai_gateway()

    async def chat(
        self,
        user: User,
        question: str,
        conversation_id: str | None = None,
        knowledge_scope: str | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """产品问答主入口。

        演示模式：
        1. 构建系统提示词
        2. 调用 gateway.chat(stream=True)
        3. 逐 token yield

        正式模式（预留）：
        1. 创建/获取会话
        2. 保存用户消息
        3. RAG 检索
        4. 构建带上下文的提示词
        5. 流式调用 LLM
        6. 保存助手消息与来源
        """
        conversation_id = conversation_id or str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        if settings.DEMO_MODE or self.db is None:
            async for event in self._demo_chat(
                question=question,
                conversation_id=conversation_id,
                message_id=message_id,
            ):
                yield event
        else:
            async for event in self._real_chat(
                user=user,
                question=question,
                conversation_id=conversation_id,
                message_id=message_id,
                knowledge_scope=knowledge_scope,
                **kwargs,
            ):
                yield event

    async def _demo_chat(
        self,
        question: str,
        conversation_id: str,
        message_id: str,
    ) -> AsyncGenerator[str, None]:
        """演示模式聊天流程。"""
        messages = [
            {"role": "system", "content": _DEMO_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        # 1. 发送 message_start 事件
        yield _sse_event("message_start", {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "role": "assistant",
        })

        # 2. 流式输出 token
        full_content = ""
        try:
            stream = await self.gateway.chat(messages=messages, stream=True)
            async for token in stream:
                full_content += token
                yield _sse_event("token", {"content": token})
        except Exception as e:
            logger.error("demo_chat_stream_error", error=str(e))
            error_msg = "抱歉，演示服务暂时不可用，请稍后重试。"
            yield _sse_event("token", {"content": error_msg})
            full_content = error_msg

        # 3. 发送参考来源（演示模式固定来源）
        yield _sse_event("reference_sources", {
            "sources": _DEMO_SOURCES,
        })

        # 4. 发送 message_complete 事件
        yield _sse_event("message_complete", {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "content": full_content,
            "finish_reason": "stop",
        })

    async def _real_chat(
        self,
        user: User,
        question: str,
        conversation_id: str,
        message_id: str,
        knowledge_scope: str | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """正式模式聊天流程（RAG + LLM）。"""
        # TODO: 实现完整的 RAG 流程
        # 1. 创建/获取会话记录
        # 2. 保存用户消息到数据库
        # 3. 执行混合检索（向量 + 关键词）
        # 4. Rerank 检索结果
        # 5. 构建带上下文的 system prompt
        # 6. 流式调用 LLM
        # 7. 保存助手消息和引用来源
        logger.warning("real_chat_not_implemented", user_id=str(user.id))
        async for event in self._demo_chat(
            question=question,
            conversation_id=conversation_id,
            message_id=message_id,
        ):
            yield event


def _sse_event(event_type: str, data: dict) -> str:
    """构造 SSE 事件字符串。"""
    return json.dumps({"event": event_type, "data": data}, ensure_ascii=False)
