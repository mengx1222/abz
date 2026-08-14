"""管理后台 Pydantic Schema — 用户管理/审计日志/数据看板/合规中心/系统设置。"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== 用户管理 ====================

class AdminUserCreate(BaseModel):
    """创建用户请求。"""
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    role_code: str = Field(..., description="角色编码")
    organization_id: uuid.UUID = Field(..., description="所属组织ID")
    team_id: Optional[uuid.UUID] = Field(None, description="所属团队ID")
    initial_password: str = Field(..., min_length=6, max_length=50, description="初始密码")


class AdminUserUpdate(BaseModel):
    """更新用户请求。"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role_code: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    team_id: Optional[uuid.UUID] = None


class AdminUserItem(BaseModel):
    """管理后台用户列表项。"""
    id: uuid.UUID
    phone: str
    name: str
    avatar_url: Optional[str] = None
    role_code: str
    role_name: str
    organization_name: str = ""
    team_name: Optional[str] = None
    status: str = "active"
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminDisableRequest(BaseModel):
    """禁用用户请求。"""
    reason: str = Field(..., min_length=1, max_length=500, description="禁用原因")


# ==================== 审计日志 ====================

class AuditLogItem(BaseModel):
    """审计日志项。"""
    id: str
    user_id: str
    user_name: str
    user_role: str
    action: str
    resource_type: str
    resource_id: str = ""
    description: str
    ip_address: str = ""
    created_at: datetime


class AuditLogExportRequest(BaseModel):
    """审计日志导出请求。"""
    filters: Optional[dict] = None
    format: str = Field(default="xlsx", description="导出格式: xlsx/csv")


# ==================== 数据看板 ====================

class OverviewStats(BaseModel):
    """总览统计数据。"""
    period: str = "month"
    user_stats: dict = Field(default_factory=dict)
    customer_stats: dict = Field(default_factory=dict)
    ai_stats: dict = Field(default_factory=dict)
    training_stats: dict = Field(default_factory=dict)
    community_stats: dict = Field(default_factory=dict)


class AiUsageStats(BaseModel):
    """AI使用分析。"""
    period: str = "month"
    total_calls: int = 0
    feature_breakdown: list[dict] = Field(default_factory=list)
    top_users: list[dict] = Field(default_factory=list)
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    token_usage: dict = Field(default_factory=dict)


class TrainingStats(BaseModel):
    """训练分析数据。"""
    period: str = "month"
    total_sessions: int = 0
    avg_score: float = 0.0
    completion_rate: float = 0.0
    scenario_popularity: list[dict] = Field(default_factory=list)
    score_distribution: list[dict] = Field(default_factory=list)


class CommunityStats(BaseModel):
    """社区分析数据。"""
    period: str = "month"
    total_posts: int = 0
    total_comments: int = 0
    active_contributors: int = 0
    category_distribution: list[dict] = Field(default_factory=list)
    top_posts: list[dict] = Field(default_factory=list)


# ==================== 合规中心 ====================

class ComplianceRuleCreate(BaseModel):
    """创建合规规则。"""
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    description: str = Field(..., max_length=500, description="规则描述")
    category: str = Field(default="regulatory", description="规则分类")
    severity: str = Field(default="violation", description="严重程度: warning/violation")
    severity_label: str = Field(default="违规", description="严重程度标签")
    keywords: list[str] = Field(default_factory=list, description="关键词列表")
    patterns: list[str] = Field(default_factory=list, description="匹配模式(正则)")
    is_active: bool = Field(default=True, description="是否启用")


class ComplianceRuleUpdate(BaseModel):
    """更新合规规则。"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    severity_label: Optional[str] = None
    keywords: Optional[list[str]] = None
    patterns: Optional[list[str]] = None
    is_active: Optional[bool] = None


class ComplianceRuleItem(BaseModel):
    """合规规则项。"""
    id: str
    name: str
    description: str
    category: str
    severity: str
    severity_label: str
    keywords: list[str] = []
    patterns: list[str] = []
    is_active: bool = True
    created_at: Optional[datetime] = None


class ComplianceReviewItem(BaseModel):
    """合规审核列表项。"""
    id: str
    type: str = ""
    type_label: str = ""
    title: str = ""
    content_preview: str = ""
    author_name: str = ""
    severity: str = ""
    status: str = "pending"
    priority: str = "medium"
    created_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class ComplianceReviewProcess(BaseModel):
    """处理审核请求。"""
    action: str = Field(..., description="处理动作: approved/rejected/needs_revision")
    comment: str = Field(..., min_length=1, max_length=500, description="处理意见")
    conditions: Optional[list[str]] = Field(None, description="附加条件(仅approved时)")


# ==================== 社区管理 ====================

class AdminPostItem(BaseModel):
    """管理后台帖子列表项。"""
    id: uuid.UUID
    title: str
    author_name: str = ""
    category: str = ""
    category_label: str = ""
    status: str = "published"
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    is_pinned: bool = False
    is_recommended: bool = False
    created_at: Optional[datetime] = None


class PinRequest(BaseModel):
    """置顶请求。"""
    is_pinned: bool = True
    pin_expiry: Optional[datetime] = None


class RecommendRequest(BaseModel):
    """推荐请求。"""
    is_recommended: bool = True
    recommend_reason: Optional[str] = None


# ==================== 话术管理 ====================

class AdminScriptItem(BaseModel):
    """管理后台话术列表项。"""
    id: str
    title: str = ""
    style: str = ""
    style_label: str = ""
    product_type: str = ""
    content_preview: str = ""
    author_name: str = ""
    status: str = "approved"
    compliance_status: str = "GREEN"
    usage_count: int = 0
    favorite_count: int = 0
    created_at: Optional[datetime] = None


class ScriptApproveRequest(BaseModel):
    """话术审批请求。"""
    action: str = Field(..., description="审批动作: approve/reject")
    comment: Optional[str] = Field(None, description="审批意见")


# ==================== 陪练场景管理 ====================

class ScenarioCreate(BaseModel):
    """创建陪练场景。"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    category: str = Field(default="initial_contact")
    difficulty: str = Field(default="easy")
    background: str = Field(default="")
    customer_persona: dict = Field(default_factory=dict)
    objectives: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int = Field(default=10)


class ScenarioUpdate(BaseModel):
    """更新陪练场景。"""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    background: Optional[str] = None
    customer_persona: Optional[dict] = None
    objectives: Optional[list[str]] = None
    success_criteria: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    estimated_duration_minutes: Optional[int] = None


class AdminScenarioItem(BaseModel):
    """管理后台陪练场景列表项。"""
    id: str
    title: str
    description: str = ""
    category: str = ""
    difficulty: str = ""
    status: str = "published"
    duration_minutes: int = 10
    usage_count: int = 0
    avg_score: float = 0.0
    tags: list[str] = []
    created_at: Optional[datetime] = None


# ==================== 系统设置 ====================

class SystemSettings(BaseModel):
    """系统设置。"""
    ai: dict = Field(default_factory=dict)
    rag: dict = Field(default_factory=dict)
    compliance: dict = Field(default_factory=dict)
    notification: dict = Field(default_factory=dict)
    community: dict = Field(default_factory=dict)


class SystemSettingsUpdate(BaseModel):
    """更新系统设置（部分更新）。"""
    ai: Optional[dict] = None
    rag: Optional[dict] = None
    compliance: Optional[dict] = None
    notification: Optional[dict] = None
    community: Optional[dict] = None
