"""客户360 API —— 客户CRUD + 互动记录 + 跟进任务 + AI分析。

REST endpoints:
- GET    /customers              — 客户列表（带筛选和分页）
- GET    /customers/{id}         — 客户详情（含互动和跟进）
- POST   /customers              — 创建客户
- PUT    /customers/{id}         — 更新客户
- DELETE /customers/{id}         — 软删除客户
- POST   /customers/{id}/interactions — 添加互动记录
- POST   /customers/{id}/followups    — 添加跟进任务
- POST   /customers/{id}/ai-analysis  — SSE 流式 AI 分析
"""
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.deps import get_current_user, get_db
from app.core.sanitize import sanitize_response_data
from app.models.user import User
from app.schemas.common import SuccessResponse, PaginatedResponse
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerInteractionCreate,
    CustomerFollowupCreate,
)
from app.services.customer_service import CustomerService

logger = get_logger()
router = APIRouter()


# ============================================================
# GET /customers — 列表
# ============================================================

@router.get(
    "",
    summary="获取客户列表",
    response_model=PaginatedResponse,
)
async def list_customers(
    request: Request,
    customer_type: str | None = Query(None, description="客户类型：prospective/active/lapsed"),
    current_stage: str | None = Query(None, description="销售阶段"),
    intention_level: int | None = Query(None, description="意向等级 1-5"),
    tag: str | None = Query(None, description="按标签筛选"),
    search: str | None = Query(None, description="搜索姓名或手机号"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """获取客户列表，支持多维筛选和搜索。"""
    request_id = getattr(request.state, "request_id", None)

    service = CustomerService(session=db)
    items, total = await service.list_customers(
        customer_type=customer_type,
        current_stage=current_stage,
        intention_level=intention_level,
        tag=tag,
        search=search,
        page=page,
        page_size=page_size,
        current_user=current_user,
    )

    # 列表接口脱敏手机号
    masked_items = sanitize_response_data(items, {"phone": "phone"})

    return PaginatedResponse.create(
        items=masked_items,
        total=total,
        page=page,
        page_size=page_size,
        request_id=request_id,
    )


# ============================================================
# GET /customers/{id} — 详情
# ============================================================

@router.get(
    "/{customer_id}",
    summary="获取客户详情",
    response_model=SuccessResponse,
)
async def get_customer(
    customer_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """获取客户详情，包含互动记录和跟进任务。"""
    request_id = getattr(request.state, "request_id", None)

    service = CustomerService(session=db)
    customer = await service.get_customer(customer_id, current_user=current_user)
    if customer is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "客户不存在"},
        )

    return SuccessResponse(data=customer, request_id=request_id)


# ============================================================
# POST /customers — 创建
# ============================================================

@router.post(
    "",
    summary="创建客户",
    response_model=SuccessResponse,
)
async def create_customer(
    body: CustomerCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """创建新客户。"""
    request_id = getattr(request.state, "request_id", None)

    service = CustomerService(session=db)
    customer = await service.create_customer(body, user_id=current_user.id, current_user=current_user)

    logger.info(
        "customer_created",
        customer_id=customer["id"],
        name=customer["name"],
        user_id=str(current_user.id),
    )

    return SuccessResponse(data=customer, request_id=request_id)


# ============================================================
# PUT /customers/{id} — 更新
# ============================================================

@router.put(
    "/{customer_id}",
    summary="更新客户",
    response_model=SuccessResponse,
)
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """更新客户信息。"""
    request_id = getattr(request.state, "request_id", None)

    service = CustomerService(session=db)
    customer = await service.update_customer(customer_id, body, user_id=current_user.id, current_user=current_user)
    if customer is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "客户不存在"},
        )

    logger.info(
        "customer_updated",
        customer_id=str(customer_id),
        user_id=str(current_user.id),
    )

    return SuccessResponse(data=customer, request_id=request_id)


# ============================================================
# DELETE /customers/{id} — 软删除
# ============================================================

@router.delete(
    "/{customer_id}",
    summary="删除客户",
    response_model=SuccessResponse,
)
async def delete_customer(
    customer_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """软删除客户。"""
    request_id = getattr(request.state, "request_id", None)

    service = CustomerService(session=db)
    success = await service.delete_customer(customer_id, current_user=current_user)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "客户不存在"},
        )

    logger.info(
        "customer_deleted",
        customer_id=str(customer_id),
        user_id=str(current_user.id),
    )

    return SuccessResponse(data={"message": "客户已删除"}, request_id=request_id)


# ============================================================
# POST /customers/{id}/interactions — 添加互动记录
# ============================================================

@router.post(
    "/{customer_id}/interactions",
    summary="添加互动记录",
    response_model=SuccessResponse,
)
async def add_interaction(
    customer_id: uuid.UUID,
    body: CustomerInteractionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """为客户添加一条互动记录。"""
    request_id = getattr(request.state, "request_id", None)

    service = CustomerService(session=db)
    interaction = await service.add_interaction(customer_id, body, user_id=current_user.id, current_user=current_user)
    if interaction is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "客户不存在"},
        )

    logger.info(
        "customer_interaction_added",
        customer_id=str(customer_id),
        type=body.type,
        user_id=str(current_user.id),
    )

    return SuccessResponse(data=interaction, request_id=request_id)


# ============================================================
# POST /customers/{id}/followups — 添加跟进任务
# ============================================================

@router.post(
    "/{customer_id}/followups",
    summary="添加跟进任务",
    response_model=SuccessResponse,
)
async def add_followup(
    customer_id: uuid.UUID,
    body: CustomerFollowupCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """为客户添加一条跟进任务。"""
    request_id = getattr(request.state, "request_id", None)

    service = CustomerService(session=db)
    followup = await service.add_followup(customer_id, body, user_id=current_user.id, current_user=current_user)
    if followup is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "客户不存在"},
        )

    logger.info(
        "customer_followup_added",
        customer_id=str(customer_id),
        user_id=str(current_user.id),
    )

    return SuccessResponse(data=followup, request_id=request_id)


# ============================================================
# POST /customers/{id}/ai-analysis — SSE 流式 AI 分析
# ============================================================

@router.post(
    "/{customer_id}/ai-analysis",
    summary="AI 客户分析（SSE 流式）",
)
async def ai_analysis(
    customer_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """对客户进行 AI 分析，返回 SSE 事件流。

    事件类型：
    - analysis_start: 分析开始
    - token: 流式文本 token
    - structured_data: 结构化分析结果
    - analysis_complete: 分析完成
    - error: 错误
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.info(
        "customer_ai_analysis_start",
        customer_id=str(customer_id),
        user_id=str(current_user.id),
        request_id=request_id,
    )

    service = CustomerService(session=db)

    async def event_stream() -> AsyncGenerator[str, None]:
        yield f"event: connected\ndata: {{\"request_id\": \"{request_id}\"}}\n\n"
        try:
            async for event in service.ai_analysis_stream(customer_id):
                yield event
        except Exception as e:
            logger.error(
                "customer_ai_analysis_stream_error",
                customer_id=str(customer_id),
                error=str(e),
            )
            import json
            error_data = json.dumps(
                {"message": "AI分析服务异常，请稍后重试"},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
