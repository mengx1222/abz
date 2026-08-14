"""通知模型：Notification（通知） + NotificationPreference（偏好设置）。"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notification(Base):
    """用户通知。"""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="接收用户ID",
    )
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="通知类型: followup/system/training/team/community/achievement",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="通知标题",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="通知内容",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="是否已读",
    )
    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="跳转链接",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        comment="附加元数据",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="已读时间",
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type!r} title={self.title!r}>"


class NotificationPreference(Base):
    """用户通知偏好设置。"""

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="用户ID",
    )
    followup_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, comment="跟进提醒",
    )
    system_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, comment="系统通知",
    )
    training_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, comment="训练提醒",
    )
    team_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, comment="团队动态",
    )
    community_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, comment="社区互动",
    )

    def __repr__(self) -> str:
        return f"<NotificationPreference id={self.id} user_id={self.user_id}>"
