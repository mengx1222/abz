"""通知中心 API：通知列表、已读、设置偏好。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.schemas.notification import (
    MarkReadRequest,
    MarkReadResponse,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreference,
    UpdatePreferenceRequest,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    type: str | None = Query(None, description="通知类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取通知列表（支持分页和类型筛选）。"""
    service = NotificationService(session=db)
    return await service.list_notifications(user.phone, type, page, page_size)


@router.post("/read", response_model=MarkReadResponse)
async def mark_notifications_read(
    req: MarkReadRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记通知已读（支持批量标记和全部标记）。"""
    service = NotificationService(session=db)
    return await service.mark_read(user.phone, req.notification_ids, req.read_all)


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取通知偏好设置。"""
    service = NotificationService(session=db)
    return await service.get_preferences(user.phone)


@router.put("/preferences", response_model=NotificationPreference)
async def update_notification_preference(
    req: UpdatePreferenceRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新通知偏好设置。"""
    service = NotificationService(session=db)
    return await service.update_preference(user.phone, req)
