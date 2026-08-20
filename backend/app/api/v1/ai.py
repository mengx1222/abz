import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.ai.service import ProductQaService
from app.agent.orchestrator import SalesAgentService
from app.agent.schemas import SalesAgentChatRequest
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.conversation_repo import ConversationRepository
from app.schemas.common import SuccessResponse

logger = get_logger()
router = APIRouter()


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------

class ProductQaChatRequest(BaseModel):
    """产品问答请求。"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    conversation_id: str | None = Field(None, description="会话ID，为空则创建新会话")
    knowledge_scope: str | None = Field(None, description="知识范围限制")


class ConversationItem(BaseModel):
    """会话列表项。"""
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ConversationDetail(BaseModel):
    """会话详情。"""
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[dict]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post(
    "/product-qa/chat",
    summary="产品问答（SSE 流式）",
)
async def product_qa_chat(
    body: ProductQaChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """产品问答 SSE 流式接口。

    返回 Server-Sent Events 流，事件类型：
    - connected: 连接成功
    - message_start: 消息开始（含 conversation_id, message_id）
    - token: 流式 token
    - reference_sources: 参考来源
    - message_complete: 消息结束
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    conversation_id = body.conversation_id or str(uuid.uuid4())

    logger.info(
        "product_qa_chat_start",
        user_id=str(current_user.id),
        conversation_id=conversation_id,
        question=body.question[:100],
        request_id=request_id,
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流。"""
        # connected 事件
        yield f"event: connected\ndata: {{\"request_id\": \"{request_id}\"}}\n\n"

        try:
            service = ProductQaService(db=db)
            async for event_json in service.chat(
                user=current_user,
                question=body.question,
                conversation_id=conversation_id,
                knowledge_scope=body.knowledge_scope,
            ):
                # event_json 已经是 JSON 字符串
                yield f"data: {event_json}\n\n"
        except Exception as e:
            logger.error(
                "product_qa_chat_error",
                user_id=str(current_user.id),
                error=str(e),
                request_id=request_id,
            )
            import json
            error_data = json.dumps(
                {"event": "error", "data": {"message": "服务异常，请稍后重试"}},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/sales-agent/chat",
    summary="AI Sales Agent（SSE 流式）",
)
async def sales_agent_chat(
    body: SalesAgentChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """AI Sales Agent SSE 流式接口（第一阶段：后端编排 + 工具链）。

    事件类型：
    - connected: 连接成功
    - agent_start: Agent 开始（request_id/session_id）
    - tool_planned: 计划执行工具（安全状态说明，非思维链）
    - tool_start / tool_result: 工具执行
    - rag_context / citation: RAG 依据与引用
    - message_delta: 最终回复流式输出
    - compliance: 合规检查结果
    - agent_complete: Agent 结束（status/message/tool_sequence）
    - error: 错误

    安全：
    - 所有工具携带当前用户，底层 Service/RAG 再次执行 RBAC/组织范围检查
    - RAG REFUSE 时不生成产品事实；Provider 失败不 fallback Mock
    - 不输出/持久化模型隐藏推理过程与内部 prompt
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    session_id = body.session_id or str(uuid.uuid4())

    logger.info(
        "sales_agent_chat_start",
        user_id=str(current_user.id),
        customer_id=body.customer_id,
        session_id=session_id,
        product_type=body.product_type,
        sales_stage=body.sales_stage,
        message=body.message[:100],
        request_id=request_id,
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        yield f"event: connected\ndata: {{\"request_id\": \"{request_id}\", \"session_id\": \"{session_id}\"}}\n\n"
        try:
            service = SalesAgentService(db=db)
            async for event_json in service.chat(
                user=current_user,
                customer_id=body.customer_id,
                message=body.message,
                product_type=body.product_type,
                sales_stage=body.sales_stage,
                session_id=session_id,
                request_id=request_id,
            ):
                yield f"data: {event_json}\n\n"
        except Exception as e:
            logger.error(
                "sales_agent_chat_error",
                user_id=str(current_user.id),
                error=str(e),
                request_id=request_id,
            )
            import json
            error_data = json.dumps(
                {"event": "error", "data": {"message": "销售助手服务异常，请稍后重试"}},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _dt_iso(dt) -> str:
    """datetime 转 ISO 字符串（缺省返回空串）。"""
    if dt is None:
        return ""
    return dt.isoformat()


@router.get(
    "/product-qa/conversations",
    summary="获取会话列表",
    response_model=SuccessResponse[list[ConversationItem]],
)
async def list_conversations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[list[ConversationItem]]:
    """获取当前用户的产品问答会话列表（ULTIMATE P0-2：DB 持久化）。

    演示模式返回空列表；生产模式按 user_id 隔离查询。
    """
    request_id = getattr(request.state, "request_id", None)

    # 演示模式返回空列表
    if settings.DEMO_MODE:
        return SuccessResponse(data=[], request_id=request_id)

    repo = ConversationRepository(db)
    convs = await repo.list_by_user(current_user.id, limit=50)
    items = [
        ConversationItem(
            id=str(c.id),
            title=c.title or "",
            created_at=_dt_iso(c.created_at),
            updated_at=_dt_iso(c.updated_at),
            message_count=c.message_count or 0,
        )
        for c in convs
    ]
    return SuccessResponse(data=items, request_id=request_id)


@router.get(
    "/product-qa/conversations/{conversation_id}",
    summary="获取会话详情",
    response_model=SuccessResponse[ConversationDetail],
)
async def get_conversation(
    conversation_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ConversationDetail]:
    """获取指定会话的详情（含消息历史）（ULTIMATE P0-2：DB 持久化）。

    演示模式返回空会话；生产模式按 user_id 归属校验，越权/不存在 404。
    """
    request_id = getattr(request.state, "request_id", None)

    # 演示模式返回空会话
    if settings.DEMO_MODE:
        detail = ConversationDetail(
            id=conversation_id,
            title="演示会话",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            messages=[],
        )
        return SuccessResponse(data=detail, request_id=request_id)

    try:
        conv_uuid = uuid.UUID(conversation_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    repo = ConversationRepository(db)
    conv = await repo.get_owned(conv_uuid, current_user.id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    rows = await repo.get_messages(conv.id, limit=100)
    messages = [
        {
            "role": m.role,
            "content": m.content,
            "created_at": _dt_iso(m.created_at),
            "finish_reason": m.finish_reason,
        }
        for m in rows
    ]
    detail = ConversationDetail(
        id=str(conv.id),
        title=conv.title or "",
        created_at=_dt_iso(conv.created_at),
        updated_at=_dt_iso(conv.updated_at),
        messages=messages,
    )
    return SuccessResponse(data=detail, request_id=request_id)
