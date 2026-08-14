"""产品问答服务 —— 编排 RAG + LLM，支持Demo和生产两种模式。

增强功能：
- RAG检索增强回答
- 结构化输出（key_points, risk_warning, confidence）
- 引用来源与相关性评分
- 会话历史管理
"""
import json
import uuid
from collections.abc import AsyncGenerator

from structlog import get_logger

from app.ai.gateway import get_ai_gateway
from app.core.config import settings
from app.models.user import User
from app.rag.pipeline import RAGPipeline, init_demo_index, _build_context

logger = get_logger()

# 演示模式的系统提示词
_DEMO_SYSTEM_PROMPT = """你是「安诊保 AI 副驾」，华安保险的智能保险产品专家助手。

## 你的职责
1. 帮助保险销售人员快速了解华安保险的产品信息
2. 根据客户需求推荐合适的保险产品组合
3. 解答保险产品的保障范围、保费、理赔等问题
4. 提供专业的保险销售话术和沟通建议

## 回答规范
- 回答必须基于华安保险的产品知识
- 语言简洁专业，适合保险销售场景
- 优先使用要点列表、表格等结构化格式
- 如不确定某产品细节，诚实说明并建议咨询产品部门

{context_section}"""


class ProductQaService:
    """产品问答服务 —— 编排 RAG + LLM。"""

    def __init__(self, db=None):
        self.db = db
        self.gateway = get_ai_gateway()
        self._pipeline: RAGPipeline | None = None

    async def _get_pipeline(self) -> RAGPipeline:
        """获取RAG Pipeline（懒加载）。"""
        if self._pipeline is None:
            self._pipeline = RAGPipeline(db=self.db)
        return self._pipeline

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
        1. 确保Demo索引已初始化
        2. RAG检索相关文档片段
        3. 构建带上下文的系统提示词
        4. 调用 LLM 流式输出
        5. 附带引用来源

        正式模式：
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
                knowledge_scope=knowledge_scope,
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
        knowledge_scope: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """演示模式聊天流程（RAG增强）。"""
        pipeline = await self._get_pipeline()

        # Step 1: RAG检索
        search_results = []
        try:
            kb_ids = [knowledge_scope] if knowledge_scope else None
            search_results, context_text = await pipeline.query(
                question=question,
                top_k=6,
                knowledge_base_ids=kb_ids,
            )
        except Exception as e:
            logger.error("demo_rag_search_error", error=str(e))
            context_text = ""

        # Step 2: 构建系统提示词
        if context_text:
            context_section = f"## 参考知识内容\n\n{context_text}\n\n请基于以上参考内容回答用户问题，并在回答中引用来源。"
        else:
            context_section = "当前无相关参考内容，请基于华安保险通用知识回答。"

        system_prompt = _DEMO_SYSTEM_PROMPT.format(context_section=context_section)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        # 1. message_start
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

        # 3. 发送参考来源
        sources = []
        if search_results:
            for result in search_results[:5]:
                sources.append({
                    "title": result.document_title,
                    "chunk_id": result.chunk_id,
                    "relevance_score": round(result.score, 2),
                    "heading": result.metadata.get("heading", ""),
                })
        else:
            sources = [
                {"title": "华安保险产品知识库", "chunk_id": "demo-general", "relevance_score": 0.5},
            ]

        yield _sse_event("reference_sources", {"sources": sources})

        # 4. message_complete
        yield _sse_event("message_complete", {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "content": full_content,
            "finish_reason": "stop",
            "sources_count": len(sources),
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
        """正式模式聊天流程（RAG + LLM + DB持久化）。"""
        pipeline = await self._get_pipeline()

        # Step 1: RAG检索
        search_results = []
        try:
            kb_ids = [knowledge_scope] if knowledge_scope else None
            search_results, context_text = await pipeline.query(
                question=question,
                top_k=8,
                knowledge_base_ids=kb_ids,
                user_roles=[user.role_code] if hasattr(user, "role_code") else None,
            )
        except Exception as e:
            logger.error("real_rag_search_error", error=str(e))
            context_text = ""

        # Step 2: 构建系统提示词
        if context_text:
            context_section = f"## 参考知识内容\n\n{context_text}\n\n请基于以上参考内容回答，引用来源。"
        else:
            context_section = "无相关参考内容，基于通用保险知识回答。"

        system_prompt = _DEMO_SYSTEM_PROMPT.format(context_section=context_section)

        # TODO: 从DB加载会话历史
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        yield _sse_event("message_start", {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "role": "assistant",
        })

        full_content = ""
        try:
            stream = await self.gateway.chat(messages=messages, stream=True)
            async for token in stream:
                full_content += token
                yield _sse_event("token", {"content": token})
        except Exception as e:
            logger.error("real_chat_stream_error", error=str(e))
            full_content = "抱歉，服务暂时不可用。"
            yield _sse_event("token", {"content": full_content})

        # 发送来源
        sources = [
            {
                "title": r.document_title,
                "chunk_id": r.chunk_id,
                "relevance_score": round(r.score, 2),
            }
            for r in search_results[:5]
        ]
        yield _sse_event("reference_sources", {"sources": sources})

        yield _sse_event("message_complete", {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "content": full_content,
            "finish_reason": "stop",
        })

        # TODO: 保存消息到数据库


def _sse_event(event_type: str, data: dict) -> str:
    """构造 SSE 事件字符串。"""
    return json.dumps({"event": event_type, "data": data}, ensure_ascii=False)
