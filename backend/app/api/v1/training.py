"""AI 陪练 API 路由。"""

import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from structlog import get_logger

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import SuccessResponse, ErrorResponse
from app.schemas.training import (
    ScenarioList,
    ScenarioDetail,
    SessionStart,
    SessionDetail,
    SessionListItem,
    TrainingScoreDetail,
    TrainingHistoryStats,
)
from app.services.training_service import TrainingService

logger = get_logger()
router = APIRouter()


# ------------------------------------------------------------------
# Request schemas
# ------------------------------------------------------------------

class SendMessageRequest(BaseModel):
    """发送消息请求。"""
    content: str = Field(..., min_length=1, max_length=5000, description="代理人消息内容")


# ------------------------------------------------------------------
# Scenarios
# ------------------------------------------------------------------

@router.get(
    "/scenarios",
    summary="获取训练场景列表",
    response_model=SuccessResponse[list[ScenarioList]],
)
async def list_scenarios(
    request: Request,
    difficulty: str | None = Query(None, description="按难度过滤: easy/medium/hard"),
    product_focus: str | None = Query(None, description="按产品类型过滤"),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[list[ScenarioList]]:
    """获取可用的训练场景列表，支持按难度和产品类型过滤。"""
    request_id = getattr(request.state, "request_id", None)
    service = TrainingService()
    scenarios = await service.get_scenarios(
        difficulty=difficulty,
        product_focus=product_focus,
    )
    return SuccessResponse(data=scenarios, request_id=request_id)


@router.get(
    "/scenarios/{scenario_id}",
    summary="获取场景详情",
    response_model=SuccessResponse[ScenarioDetail],
)
async def get_scenario(
    scenario_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[ScenarioDetail]:
    """获取指定训练场景的详细信息。"""
    request_id = getattr(request.state, "request_id", None)
    service = TrainingService()
    scenario = await service.get_scenario(scenario_id)
    if scenario is None:
        from fastapi import status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCENARIO_NOT_FOUND", "message": f"场景 {scenario_id} 不存在"},
        )
    return SuccessResponse(data=scenario, request_id=request_id)


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

@router.post(
    "/sessions",
    summary="开始训练会话",
    response_model=SuccessResponse[SessionDetail],
)
async def start_session(
    body: SessionStart,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[SessionDetail]:
    """基于指定场景开始一个新的 AI 陪练会话。"""
    request_id = getattr(request.state, "request_id", None)
    service = TrainingService()
    try:
        session = await service.start_session(
            user_id=str(current_user.id),
            scenario_id=body.scenario_id,
        )
    except ValueError as e:
        from fastapi import status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_SCENARIO", "message": str(e)},
        )
    return SuccessResponse(data=session, request_id=request_id)


@router.get(
    "/sessions",
    summary="获取训练会话列表",
    response_model=SuccessResponse[list[SessionListItem]],
)
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[list[SessionListItem]]:
    """获取当前用户的训练会话列表。"""
    request_id = getattr(request.state, "request_id", None)
    service = TrainingService()
    sessions = await service.list_sessions(user_id=str(current_user.id))
    return SuccessResponse(data=sessions, request_id=request_id)


@router.get(
    "/sessions/{session_id}",
    summary="获取会话详情",
    response_model=SuccessResponse[SessionDetail],
)
async def get_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[SessionDetail]:
    """获取指定训练会话的详情，包含所有消息记录。"""
    request_id = getattr(request.state, "request_id", None)
    service = TrainingService()
    session = await service.get_session(
        session_id=session_id,
        user_id=str(current_user.id),
    )
    if session is None:
        from fastapi import status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "会话不存在或无权访问"},
        )
    return SuccessResponse(data=session, request_id=request_id)


@router.post(
    "/sessions/{session_id}/messages",
    summary="发送消息 (SSE 流式)",
)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """发送代理人消息，SSE 流式返回 AI 客户响应和教练辅导。

    SSE 事件序列：
    - message_start: 消息开始
    - token: 流式客户回复
    - coaching: 教练辅导提示
    - turn_complete: 回合完成
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.info(
        "training_send_message",
        user_id=str(current_user.id),
        session_id=session_id,
        content_length=len(body.content),
        request_id=request_id,
    )

    service = TrainingService()

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event_json in service.send_message(
                session_id=session_id,
                user_id=str(current_user.id),
                content=body.content,
            ):
                yield f"data: {event_json}\n\n"
        except Exception as e:
            logger.error(
                "training_send_message_error",
                user_id=str(current_user.id),
                session_id=session_id,
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
    "/sessions/{session_id}/complete",
    summary="完成训练 (SSE 流式)",
)
async def complete_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """结束训练会话，SSE 流式返回评分报告。

    SSE 事件序列：
    - scoring_start: 评分开始
    - token: 分析过程文字
    - score_data: 评分数据
    - scoring_complete: 评分完成
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.info(
        "training_complete_session",
        user_id=str(current_user.id),
        session_id=session_id,
        request_id=request_id,
    )

    service = TrainingService()

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event_json in service.complete_session(
                session_id=session_id,
                user_id=str(current_user.id),
            ):
                yield f"data: {event_json}\n\n"
        except Exception as e:
            logger.error(
                "training_complete_session_error",
                user_id=str(current_user.id),
                session_id=session_id,
                error=str(e),
                request_id=request_id,
            )
            import json
            error_data = json.dumps(
                {"event": "error", "data": {"message": "评分服务异常，请稍后重试"}},
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


# ------------------------------------------------------------------
# Stats
# ------------------------------------------------------------------

@router.get(
    "/stats",
    summary="获取训练统计",
    response_model=SuccessResponse[TrainingHistoryStats],
)
async def get_stats(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[TrainingHistoryStats]:
    """获取当前用户的训练历史统计数据。"""
    request_id = getattr(request.state, "request_id", None)
    service = TrainingService()
    stats = await service.get_stats(user_id=str(current_user.id))
    return SuccessResponse(data=stats, request_id=request_id)
