"""Dashboard API：概览统计、AI建议、快捷数据。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import DashboardService

router = APIRouter()
dashboard_service = DashboardService()


@router.get("", response_model=DashboardOverview)
async def get_dashboard(user=Depends(get_current_user)):
    """获取 Dashboard 概览：问候语、今日统计、AI建议、快捷操作、最近活动。"""
    user_name = user.name or "代理人"
    return await dashboard_service.get_overview(user.phone, user_name)
