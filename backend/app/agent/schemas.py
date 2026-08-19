"""AI Sales Agent —— API 输入/输出 Contract。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SalesAgentChatRequest(BaseModel):
    """AI Sales Agent 对话请求。

    - customer_id 必填（Agent 只处理当前用户组织范围内有权访问的客户）
    - message: 用户意图/消息（如"客户想了解医疗险，帮我准备沟通要点"）
    - product_type: 可选产品类型（如"医疗险"），用于限定 RAG 产品边界
    - sales_stage: 可选销售阶段（initial_contact/needs_analysis/proposal/negotiation/closing/follow_up）
    - session_id: 会话 ID（为空创建新会话；服务端做最小上下文管理）
    """

    customer_id: str = Field(..., min_length=1, max_length=64, description="客户 ID")
    message: str = Field(..., min_length=1, max_length=2000, description="用户意图/消息")
    product_type: str | None = Field(None, max_length=64, description="产品类型（如医疗险）")
    sales_stage: str | None = Field(None, max_length=32, description="销售阶段")
    session_id: str | None = Field(None, max_length=64, description="会话 ID")
