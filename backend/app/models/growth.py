"""成长体系模型：UserAchievement（用户成就解锁记录）。"""
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserAchievement(Base):
    """用户成就解锁记录。

    成就定义本身是静态的（可配置），此模型跟踪用户的解锁状态。
    """

    __tablename__ = "user_achievements"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    achievement_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="成就编码（如 first_call, ten_deals）",
    )
    achievement_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="成就名称",
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="成就描述",
    )
    category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="sales",
        comment="成就类别: sales/training/community/knowledge/system",
    )
    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="成就图标标识",
    )
    is_unlocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="是否已解锁",
    )
    unlocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="解锁时间",
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        comment="当前进度",
    )
    target: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
        comment="目标值",
    )

    def __repr__(self) -> str:
        return f"<UserAchievement id={self.id} code={self.achievement_code!r} unlocked={self.is_unlocked}>"
