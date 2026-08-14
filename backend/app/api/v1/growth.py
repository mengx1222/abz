"""成长体系 API：统计数据、能力评估、学习进度、排行榜、成就系统。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.schemas.growth import (
    AchievementList,
    CourseDetail,
    GrowthOverview,
    LeaderboardResponse,
)
from app.services.growth_service import GrowthService

router = APIRouter()


@router.get("/overview", response_model=GrowthOverview)
async def get_growth_overview(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取成长概览：月度统计、周趋势、能力评分、学习进度、等级信息。"""
    service = GrowthService(session=db)
    return await service.get_overview(user.id)


@router.get("/courses/{course_id}", response_model=CourseDetail | None)
async def get_course_detail(
    course_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取课程详情（含课时列表）。"""
    service = GrowthService(session=db)
    return await service.get_course_detail(course_id, user.id)


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: str = Query("month", description="排行榜周期：week/month/quarter"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取排行榜。"""
    service = GrowthService(session=db)
    return await service.get_leaderboard(period, user.id)


@router.get("/achievements", response_model=AchievementList)
async def get_achievements(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取成就列表（已解锁 + 未解锁）。"""
    service = GrowthService(session=db)
    return await service.get_achievements(user.id)
