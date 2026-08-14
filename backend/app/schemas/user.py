from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class UserLogin(BaseModel):
    """登录请求。支持手机号+验证码（演示模式）或手机号+密码（正式模式）。"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    verification_code: str | None = Field(default=None, max_length=10, description="验证码（演示模式使用888888）")
    password: str | None = Field(default=None, max_length=100, description="密码（正式模式）")


class TokenResponse(BaseModel):
    """JWT token 响应。"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="access token 有效期（秒）")


class RefreshRequest(BaseModel):
    """刷新 token 请求。"""
    refresh_token: str


class UserOut(BaseModel):
    """用户信息输出。"""
    id: uuid.UUID
    phone: str
    name: str
    avatar_url: Optional[str] = None
    role_code: str
    role_name: str
    organization_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None
    status: str
    last_login_at: Optional[datetime] = None
    demo_mode: bool
    created_at: datetime

    model_config = {"from_attributes": True}
