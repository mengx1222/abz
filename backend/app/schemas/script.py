"""话术 Pydantic schemas。"""
from datetime import datetime
from pydantic import BaseModel, Field


# ---- 话术生成 ----

class CustomerContext(BaseModel):
    """客户上下文。"""
    name: str = Field("", description="客户姓名")
    age: int | None = Field(None, description="客户年龄")
    customer_type: str | None = Field(None, description="客户类型")
    stage: str | None = Field(None, description="销售阶段")
    objection: str | None = Field(None, description="客户异议")
    product_type: str | None = Field(None, description="产品类型")
    insurance_knowledge: str | None = Field(None, description="保险认知水平")


class ScriptGenerateRequest(BaseModel):
    """生成话术请求。"""
    customer_context: CustomerContext = Field(..., description="客户上下文")
    style: str | None = Field(None, description="指定风格（不指定则生成全部4种）")
    product_type: str | None = Field(None, description="产品类型")


# ---- 合规检查 ----

class ComplianceIssue(BaseModel):
    """合规问题项。"""
    rule: str = Field(..., description="命中规则")
    matched_text: str = Field(..., description="匹配文本")
    suggestion: str = Field(..., description="修改建议")


class ComplianceResult(BaseModel):
    """合规检查结果。"""
    status: str = Field(..., description="GREEN/YELLOW/RED")
    score: int = Field(..., description="合规分数 0-100")
    issues: list[ComplianceIssue] = Field(default_factory=list)


class ComplianceCheckRequest(BaseModel):
    """合规检查请求。"""
    text: str = Field(..., min_length=1, max_length=5000, description="待检查文本")


# ---- 话术 CRUD ----

class ScriptOut(BaseModel):
    """话术列表项。"""
    id: str
    title: str
    style: str
    product_type: str | None
    compliance_status: str
    status: str
    favorited_count: int
    usage_count: int
    created_at: str
    updated_at: str
    customer_context: dict | None = None


class ScriptDetail(ScriptOut):
    """话术详情。"""
    content: str | None = None
    compliance_issues: dict | None = None
    version: int = 1


class ScriptListFilter(BaseModel):
    """话术列表过滤。"""
    style: str | None = None
    product_type: str | None = None
    compliance_status: str | None = None
    status: str | None = None
    search: str | None = None
