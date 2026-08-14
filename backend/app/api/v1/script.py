"""AI话术 API —— 话术生成 + 合规检查 + CRUD。"""
import json
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from structlog import get_logger

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.script import (
    ComplianceCheckRequest,
    CustomerContext,
    ScriptGenerateRequest,
)
from app.services.script_service import ScriptService
from app.services.compliance_service import check_compliance

logger = get_logger()
router = APIRouter()


# ---- Endpoints ----

@router.post(
    "/generate",
    summary="AI生成话术（SSE流式）",
)
async def generate_scripts(
    body: ScriptGenerateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """AI多风格话术生成，SSE流式返回。

    支持4种风格：亲和型、专业型、数据驱动型、简洁型。
    每种风格独立生成，附带合规检查结果。
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    async def event_stream():
        yield f"event: connected\ndata: {{\"request_id\": \"{request_id}\"}}\n\n"
        service = ScriptService()
        try:
            async for event_json in service.generate_scripts(
                customer_context=body.customer_context.model_dump(),
                style=body.style,
                product_type=body.product_type,
            ):
                yield f"data: {event_json}\n\n"
        except Exception as e:
            logger.error("script_generation_error", error=str(e))
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': '话术生成失败'}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/check-compliance",
    summary="合规检查",
    response_model=SuccessResponse,
)
async def check_compliance_endpoint(
    body: ComplianceCheckRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """对话术文本进行合规检查。"""
    request_id = getattr(request.state, "request_id", None)
    result = check_compliance(body.text)
    return SuccessResponse(data=result, request_id=request_id)


@router.get(
    "",
    summary="获取话术列表",
    response_model=SuccessResponse,
)
async def list_scripts(
    request: Request,
    style: str | None = None,
    product_type: str | None = None,
    compliance_status: str | None = None,
    status: str | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """获取话术列表。"""
    request_id = getattr(request.state, "request_id", None)
    service = ScriptService()
    scripts = service.get_scripts({
        "style": style,
        "product_type": product_type,
        "compliance_status": compliance_status,
        "status": status,
        "search": search,
    })
    return SuccessResponse(data=scripts, request_id=request_id)


@router.get(
    "/{script_id}",
    summary="获取话术详情",
    response_model=SuccessResponse,
)
async def get_script(
    script_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """获取话术详情。"""
    request_id = getattr(request.state, "request_id", None)
    service = ScriptService()
    script = service.get_script(script_id)
    if not script:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "话术不存在"})
    return SuccessResponse(data=script, request_id=request_id)


class ScriptCreateBody(BaseModel):
    title: str = Field(..., min_length=1)
    style: str = "professional"
    content: str | None = None
    product_type: str | None = None
    customer_context: dict | None = None
    status: str = "draft"


class ScriptUpdateBody(BaseModel):
    title: str | None = None
    content: str | None = None
    product_type: str | None = None
    compliance_status: str | None = None
    status: str | None = None


@router.post(
    "",
    summary="创建话术",
    response_model=SuccessResponse,
)
async def create_script(
    body: ScriptCreateBody,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """创建话术。"""
    request_id = getattr(request.state, "request_id", None)
    service = ScriptService()
    script = service.create_script(body.model_dump())
    return SuccessResponse(data=script, request_id=request_id)


@router.put(
    "/{script_id}",
    summary="更新话术",
    response_model=SuccessResponse,
)
async def update_script(
    script_id: str,
    body: ScriptUpdateBody,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """更新话术内容（自动重新合规检查）。"""
    request_id = getattr(request.state, "request_id", None)
    service = ScriptService()
    script = service.update_script(script_id, body.model_dump(exclude_none=True))
    if not script:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "话术不存在"})
    return SuccessResponse(data=script, request_id=request_id)


@router.delete(
    "/{script_id}",
    summary="删除话术",
    response_model=SuccessResponse,
)
async def delete_script(
    script_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """删除话术。"""
    request_id = getattr(request.state, "request_id", None)
    service = ScriptService()
    if not service.delete_script(script_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "话术不存在"})
    return SuccessResponse(data={"message": "话术已删除"}, request_id=request_id)


@router.post(
    "/{script_id}/favorite",
    summary="收藏话术",
    response_model=SuccessResponse,
)
async def toggle_favorite(
    script_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """收藏话术。"""
    request_id = getattr(request.state, "request_id", None)
    service = ScriptService()
    script = service.toggle_favorite(script_id)
    if not script:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "话术不存在"})
    return SuccessResponse(data=script, request_id=request_id)
