"""add_notification_growth_audit_tables

Revision ID: 0006_notification_growth_audit
Revises: 0005_remaining
Create Date: 2025-03-15

创建新模型表: notifications, notification_preferences, user_achievements, audit_logs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0006_notification_growth_audit"
down_revision: Union[str, None] = "0005_remaining"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BASE_COLS = lambda: [
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column("created_by", UUID(as_uuid=True), nullable=True),
    sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
    sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
]


def upgrade() -> None:
    # ============================================================
    # 1. notifications — 用户通知
    # ============================================================
    op.create_table(
        "notifications",
        *_BASE_COLS(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("type", sa.String(30), nullable=False, comment="通知类型"),
        sa.Column("title", sa.String(200), nullable=False, comment="通知标题"),
        sa.Column("content", sa.Text, nullable=False, comment="通知内容"),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false", comment="是否已读"),
        sa.Column("action_url", sa.String(500), nullable=True, comment="跳转链接"),
        sa.Column("metadata", JSONB, nullable=True, server_default="{}", comment="附加元数据"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True, comment="已读时间"),
    )
    op.create_index("ix_notifications_user", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_read", "notifications", ["is_read"])

    # ============================================================
    # 2. notification_preferences — 通知偏好
    # ============================================================
    op.create_table(
        "notification_preferences",
        *_BASE_COLS(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("followup_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("system_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("training_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("team_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("community_enabled", sa.Boolean, nullable=False, server_default="true"),
    )

    # ============================================================
    # 3. user_achievements — 用户成就
    # ============================================================
    op.create_table(
        "user_achievements",
        *_BASE_COLS(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("achievement_code", sa.String(50), nullable=False, comment="成就编码"),
        sa.Column("achievement_name", sa.String(100), nullable=False, comment="成就名称"),
        sa.Column("description", sa.String(255), nullable=True, comment="成就描述"),
        sa.Column("category", sa.String(30), nullable=False, server_default="sales", comment="成就类别"),
        sa.Column("icon", sa.String(50), nullable=True, comment="成就图标标识"),
        sa.Column("is_unlocked", sa.Boolean, nullable=False, server_default="false", comment="是否已解锁"),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True, comment="解锁时间"),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0", comment="当前进度"),
        sa.Column("target", sa.Integer, nullable=False, server_default="1", comment="目标值"),
    )
    op.create_index("ix_user_achievements_user", "user_achievements", ["user_id"])
    op.create_index("ix_user_achievements_code", "user_achievements", ["achievement_code"])

    # ============================================================
    # 4. audit_logs — 审计日志
    # ============================================================
    op.create_table(
        "audit_logs",
        *_BASE_COLS(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.String(50), nullable=False, comment="操作动作"),
        sa.Column("resource_type", sa.String(50), nullable=False, comment="资源类型"),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True, comment="资源ID"),
        sa.Column("description", sa.String(500), nullable=False, comment="操作描述"),
        sa.Column("detail", JSONB, nullable=True, server_default="{}", comment="操作详情"),
        sa.Column("ip_address", sa.String(50), nullable=True, comment="IP地址"),
        sa.Column("user_agent", sa.String(500), nullable=True, comment="用户代理"),
        sa.Column("status", sa.String(20), nullable=False, server_default="success", comment="操作结果"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("user_achievements")
    op.drop_table("notification_preferences")
    op.drop_table("notifications")
