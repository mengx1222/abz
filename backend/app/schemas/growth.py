"""成长体系 Schema：统计数据、能力评估、学习进度、排行榜。"""

from datetime import date, datetime
from pydantic import BaseModel, Field


# ---- 月度统计 ----

class MonthlyStatItem(BaseModel):
    label: str
    value: str
    unit: str
    change: str
    up: bool


# ---- 周趋势 ----

class WeeklyTrendItem(BaseModel):
    day: str
    calls: int
    deals: int


# ---- 能力雷达 ----

class AbilityScore(BaseModel):
    label: str
    score: int  # 0-100


# ---- 学习课程 ----

class LearningCourse(BaseModel):
    id: str
    title: str
    progress: int  # 0-100
    total: str
    status: str  # 进行中 / 已完成
    category: str = ""
    description: str = ""


# ---- 排行榜 ----

class LeaderboardItem(BaseModel):
    rank: int
    user_name: str
    org_name: str
    score: int
    avatar: str = ""


# ---- 成长概览 ----

class GrowthOverview(BaseModel):
    monthly_stats: list[MonthlyStatItem]
    weekly_trend: list[WeeklyTrendItem]
    ability_scores: list[AbilityScore]
    learning_courses: list[LearningCourse]
    level: int = Field(description="当前等级")
    level_name: str = Field(description="等级名称")
    exp_current: int = Field(description="当前经验值")
    exp_next: int = Field(description="升级所需经验值")
    total_exp: int = Field(description="累计经验值")


# ---- 学习课程详情 ----

class CourseDetail(BaseModel):
    id: str
    title: str
    description: str
    category: str
    progress: int
    total_lessons: int
    completed_lessons: int
    status: str
    lessons: list[dict] = Field(default_factory=list)


# ---- 成就 ----

class AchievementItem(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    unlocked_at: datetime | None = None
    is_unlocked: bool = False
    category: str = ""


class AchievementList(BaseModel):
    unlocked: list[AchievementItem]
    locked: list[AchievementItem]


# ---- 排行榜响应 ----

class LeaderboardResponse(BaseModel):
    period: str = "month"  # week / month / quarter
    leaderboard: list[LeaderboardItem]
    my_rank: LeaderboardItem | None = None
