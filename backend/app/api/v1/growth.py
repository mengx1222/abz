"""成长体系 API：统计数据、能力评估、学习进度、排行榜、成就系统。"""
from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.schemas.growth import (
    AchievementList,
    CourseDetail,
    GrowthOverview,
    LeaderboardResponse,
)
from app.services.growth_service import GrowthService

router = APIRouter()
growth_service = GrowthService()


@router.get("/overview", response_model=GrowthOverview)
async def get_growth_overview(user=Depends(get_current_user)):
    """获取成长概览：月度统计、周趋势、能力评分、学习进度、等级信息。"""
    return await growth_service.get_overview(user.phone)


@router.get("/courses/{course_id}", response_model=CourseDetail | None)
async def get_course_detail(course_id: str, user=Depends(get_current_user)):
    """获取课程详情（含课时列表）。"""
    return await growth_service.get_course_detail(course_id, user.phone)


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: str = Query("month", description="排行榜周期：week/month/quarter"),
    user=Depends(get_current_user),
):
    """获取排行榜。"""
    return await growth_service.get_leaderboard(period, user.phone)


@router.get("/achievements", response_model=AchievementList)
async def get_achievements(user=Depends(get_current_user)):
    """获取成就列表（已解锁 + 未解锁）。"""
    return await growth_service.get_achievements(user.phone)
