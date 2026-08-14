"""AI 陪练 —— Pydantic 请求/响应 Schema。"""

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Customer Persona
# ------------------------------------------------------------------

class CustomerPersona(BaseModel):
    """客户人设。"""
    name: str = Field(..., description="客户姓名")
    age: int = Field(..., description="年龄")
    personality: str = Field(..., description="性格特点")
    mood: str = Field(..., description="当前情绪")
    background: str = Field(..., description="背景信息")
    insurance_knowledge: str = Field(..., description="保险认知水平")
    key_objections: list[str] = Field(default_factory=list, description="关键异议")


# ------------------------------------------------------------------
# Scenario
# ------------------------------------------------------------------

class ScenarioList(BaseModel):
    """场景列表项。"""
    id: str
    title: str
    description: str
    difficulty: str
    product_focus: str | None = None
    sales_stage: str | None = None
    duration_minutes: int
    customer_persona: CustomerPersona


class ScenarioDetail(ScenarioList):
    """场景详情。"""
    evaluation_criteria: dict = Field(default_factory=dict)


# ------------------------------------------------------------------
# Session
# ------------------------------------------------------------------

class SessionStart(BaseModel):
    """开始训练请求。"""
    scenario_id: str = Field(..., description="场景ID")


class SessionListItem(BaseModel):
    """会话列表项。"""
    id: str
    scenario_id: str | None = None
    scenario_title: str | None = None
    status: str
    started_at: str
    completed_at: str | None = None
    message_count: int
    total_score: float | None = None


class MessageItem(BaseModel):
    """消息项。"""
    id: str
    role: str
    content: str
    created_at: str
    score: float | None = None
    coaching_hint: dict | None = None


class SessionDetail(SessionListItem):
    """会话详情。"""
    messages: list[MessageItem] = Field(default_factory=list)


# ------------------------------------------------------------------
# Score
# ------------------------------------------------------------------

class RadarData(BaseModel):
    """雷达图数据。"""
    labels: list[str] = Field(default_factory=lambda: ["产品准确性", "客户共情", "促单动作"])
    values: list[float] = Field(default_factory=list)


class TrainingScoreDetail(BaseModel):
    """训练评分详情。"""
    session_id: str
    scenario_title: str | None = None
    total_score: float
    product_accuracy: float
    empathy: float
    closing_action: float
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    radar: RadarData | None = None


# ------------------------------------------------------------------
# Stats
# ------------------------------------------------------------------

class TrendItem(BaseModel):
    """趋势项。"""
    date: str
    avg_score: float
    session_count: int


class TrainingHistoryStats(BaseModel):
    """训练历史统计。"""
    total_sessions: int = 0
    completed_sessions: int = 0
    avg_score: float | None = None
    avg_product_accuracy: float | None = None
    avg_empathy: float | None = None
    avg_closing_action: float | None = None
    best_score: float | None = None
    trend: list[TrendItem] = Field(default_factory=list)
    difficulty_distribution: dict[str, int] = Field(
        default_factory=lambda: {"easy": 0, "medium": 0, "hard": 0}
    )
    product_focus_distribution: dict[str, int] = Field(default_factory=dict)
