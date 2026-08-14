import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.ai.service import ProductQaService
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.user import User
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


@router.get(
    "/product-qa/conversations",
    summary="获取会话列表",
    response_model=SuccessResponse[list[ConversationItem]],
)
async def list_conversations(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[list[ConversationItem]]:
    """获取当前用户的产品问答会话列表。

    演示模式返回空列表。
    """
    request_id = getattr(request.state, "request_id", None)

    # 演示模式返回空列表
    if settings.DEMO_MODE:
        return SuccessResponse(data=[], request_id=request_id)

    # TODO: 从数据库查询会话列表
    return SuccessResponse(data=[], request_id=request_id)


@router.get(
    "/product-qa/conversations/{conversation_id}",
    summary="获取会话详情",
    response_model=SuccessResponse[ConversationDetail],
)
async def get_conversation(
    conversation_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[ConversationDetail]:
    """获取指定会话的详情（含消息历史）。

    演示模式返回空会话。
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

    # TODO: 从数据库查询会话详情
    detail = ConversationDetail(
        id=conversation_id,
        title="",
        created_at="",
        updated_at="",
        messages=[],
    )
    return SuccessResponse(data=detail, request_id=request_id)
