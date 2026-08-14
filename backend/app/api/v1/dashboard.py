"""Dashboard API：概览统计、AI建议、快捷数据。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("", response_model=DashboardOverview)
async def get_dashboard(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Dashboard 概览：问候语、今日统计、AI建议、快捷操作、最近活动。"""
    user_name = user.name or "代理人"
    service = DashboardService(session=db)
    return await service.get_overview(user.id, user_name)
