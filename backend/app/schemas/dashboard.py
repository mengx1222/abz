"""Dashboard Schema：概览统计、AI建议、快捷数据。"""

from datetime import datetime
from pydantic import BaseModel, Field


class TodayStat(BaseModel):
    label: str
    value: str
    sub: str
    trend: str = "neutral"  # up / down / neutral


class AiSuggestion(BaseModel):
    id: str
    title: str
    description: str
    tag: str
    tag_variant: str  # error / warning / default / success
    action_url: str | None = None
    created_at: datetime


class QuickAction(BaseModel):
    label: str
    icon: str
    path: str
    color: str


class RecentActivity(BaseModel):
    id: str
    type: str  # call / deal / followup / ai_query / training
    title: str
    description: str
    time: str
    icon: str = ""


class DashboardOverview(BaseModel):
    greeting: str
    user_name: str
    today_stats: list[TodayStat]
    ai_suggestions: list[AiSuggestion]
    quick_actions: list[QuickAction]
    recent_activities: list[RecentActivity]
    unread_notifications: int = 0
