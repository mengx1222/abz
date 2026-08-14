"""客户360 Pydantic v2 请求/响应 schemas。"""
from datetime import datetime
import uuid

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    """创建客户请求。"""
    name: str = Field(..., min_length=1, max_length=100, description="客户姓名")
    age: int | None = Field(None, ge=0, le=150, description="年龄")
    gender: str | None = Field(None, description="性别：male/female")
    phone: str | None = Field(None, max_length=20, description="手机号")
    customer_type: str = Field("prospective", description="客户类型：prospective/active/lapsed")
    tags: list[str] | None = Field(None, description="标签名称列表")
    insurance_type: str | None = Field(None, description="感兴趣的保险类型")
    current_stage: str = Field("initial_contact", description="销售阶段")
    intention_level: int = Field(3, ge=1, le=5, description="意向等级 1-5")
    source_channel: str | None = Field(None, description="来源渠道")
    notes: str | None = Field(None, description="备注")


class CustomerUpdate(BaseModel):
    """更新客户请求。"""
    name: str | None = Field(None, max_length=100)
    age: int | None = Field(None, ge=0, le=150)
    gender: str | None = None
    phone: str | None = Field(None, max_length=20)
    customer_type: str | None = None
    tags: list[str] | None = None
    insurance_type: str | None = None
    current_stage: str | None = None
    intention_level: int | None = Field(None, ge=1, le=5)
    source_channel: str | None = None
    notes: str | None = None


class CustomerListFilter(BaseModel):
    """客户列表筛选条件。"""
    customer_type: str | None = None
    current_stage: str | None = None
    intention_level: int | None = None
    tag: str | None = None
    search: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class InteractionOut(BaseModel):
    """互动记录输出。"""
    id: uuid.UUID
    customer_id: uuid.UUID
    type: str
    direction: str
    content: str | None = None
    outcome: str | None = None
    next_followup_date: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FollowupOut(BaseModel):
    """跟进任务输出。"""
    id: uuid.UUID
    customer_id: uuid.UUID
    scheduled_date: datetime
    completed_date: datetime | None = None
    status: str
    content: str | None = None
    result: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerOut(BaseModel):
    """客户列表项输出。"""
    id: uuid.UUID
    name: str
    age: int | None = None
    gender: str | None = None
    phone: str | None = None
    customer_type: str
    tags: list[str] | None = None
    insurance_type: str | None = None
    current_stage: str
    intention_level: int
    source_channel: str | None = None
    notes: str | None = None
    assigned_to: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerDetail(CustomerOut):
    """客户详情（含互动和跟进）。"""
    interactions: list[InteractionOut] = []
    followups: list[FollowupOut] = []


class CustomerInteractionCreate(BaseModel):
    """添加互动记录请求。"""
    type: str = Field(..., description="互动类型：phone/wechat/f2f/email/other")
    direction: str = Field("outbound", description="方向：inbound/outbound")
    content: str | None = Field(None, description="互动内容")
    outcome: str | None = Field(None, description="互动结果")
    next_followup_date: datetime | None = Field(None, description="下次跟进日期")


class CustomerFollowupCreate(BaseModel):
    """添加跟进任务请求。"""
    scheduled_date: datetime = Field(..., description="计划跟进日期")
    content: str | None = Field(None, description="跟进内容")
    status: str = Field("pending", description="状态：pending/completed/cancelled")
    result: str | None = Field(None, description="跟进结果")


class CustomerAnalysisResult(BaseModel):
    """AI 客户分析结果。"""
    customer_profile: str = Field(..., description="AI分析 - 客户画像")
    purchase_intent: int = Field(..., ge=1, le=10, description="AI分析 - 购买意向 1-10")
    price_sensitivity: str = Field(..., description="AI分析 - 价格敏感度：low/medium/high")
    recommended_products: list[str] = Field(default_factory=list, description="AI分析 - 推荐产品")
    recommended_actions: list[str] = Field(default_factory=list, description="AI分析 - 建议行动")
    forbidden_actions: list[str] = Field(default_factory=list, description="AI分析 - 禁忌事项")
    risk_notes: list[str] = Field(default_factory=list, description="AI分析 - 风险提示")

    model_config = {"from_attributes": True}
