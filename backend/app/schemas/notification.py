"""通知中心 Schema：通知列表、已读、设置偏好。"""

from datetime import datetime
from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    id: str
    type: str  # system / followup / training / team / achievement
    title: str
    content: str
    time: str  # 相对时间描述
    created_at: datetime
    read: bool
    action_url: str | None = None
    metadata: dict = Field(default_factory=dict)


class NotificationListResponse(BaseModel):
    notifications: list[NotificationItem]
    total: int
    unread_count: int
    page: int
    page_size: int


class MarkReadRequest(BaseModel):
    notification_ids: list[str] = Field(default_factory=list)
    read_all: bool = False


class MarkReadResponse(BaseModel):
    updated_count: int


class NotificationPreference(BaseModel):
    type: str
    label: str
    enabled: bool
    channel: list[str] = Field(default_factory=lambda: ["in_app"])


class NotificationPreferencesResponse(BaseModel):
    preferences: list[NotificationPreference]


class UpdatePreferenceRequest(BaseModel):
    type: str
    enabled: bool | None = None
    channel: list[str] | None = None
