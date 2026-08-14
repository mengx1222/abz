"""add_customer_training_conversation_tables

Revision ID: 0005_remaining
Revises: 0004_community
Create Date: 2025-03-01

创建缺失的表: customer_tags, customers, customer_interactions, customer_followups,
training_scenarios, training_sessions, training_messages, training_scores,
conversations, messages
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0005_remaining"
down_revision: Union[str, None] = "0004_community"
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
    # 1. customer_tags — 客户标签定义
    # ============================================================
    op.create_table(
        "customer_tags",
        *_BASE_COLS(),
        sa.Column("name", sa.String(50), unique=True, nullable=False, comment="标签名称"),
        sa.Column("category", sa.String(50), nullable=True, comment="标签分类"),
    )

    # ============================================================
    # 2. customers — 客户表
    # ============================================================
    op.create_table(
        "customers",
        *_BASE_COLS(),
        sa.Column("name", sa.String(100), nullable=False, comment="客户姓名"),
        sa.Column("age", sa.Integer, nullable=True, comment="年龄"),
        sa.Column("gender", sa.String(10), nullable=True, comment="性别"),
        sa.Column("phone", sa.String(20), nullable=True, comment="手机号"),
        sa.Column("customer_type", sa.String(20), nullable=False, server_default="prospective", comment="客户类型"),
        sa.Column("tags", JSONB, nullable=True, comment="标签ID列表"),
        sa.Column("insurance_type", sa.String(100), nullable=True, comment="感兴趣的保险类型"),
        sa.Column("current_stage", sa.String(30), nullable=False, server_default="initial_contact", comment="销售阶段"),
        sa.Column("intention_level", sa.Integer, nullable=False, server_default="3", comment="意向等级 1-5"),
        sa.Column("source_channel", sa.String(50), nullable=True, comment="来源渠道"),
        sa.Column("notes", sa.Text, nullable=True, comment="备注"),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="负责代理人"),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, comment="所属组织"),
    )
    op.create_index("ix_customers_type", "customers", ["customer_type"])
    op.create_index("ix_customers_stage", "customers", ["current_stage"])
    op.create_index("ix_customers_assigned_to", "customers", ["assigned_to"])
    op.create_index("ix_customers_org", "customers", ["organization_id"])

    # ============================================================
    # 3. customer_interactions — 客户互动记录
    # ============================================================
    op.create_table(
        "customer_interactions",
        *_BASE_COLS(),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, comment="客户ID"),
        sa.Column("type", sa.String(20), nullable=False, comment="互动类型"),
        sa.Column("direction", sa.String(20), nullable=False, server_default="outbound", comment="方向"),
        sa.Column("content", sa.Text, nullable=True, comment="互动内容"),
        sa.Column("outcome", sa.Text, nullable=True, comment="互动结果"),
        sa.Column("next_followup_date", sa.DateTime(timezone=True), nullable=True, comment="下次跟进日期"),
    )
    op.create_index("ix_customer_interactions_customer", "customer_interactions", ["customer_id"])

    # ============================================================
    # 4. customer_followups — 客户跟进任务
    # ============================================================
    op.create_table(
        "customer_followups",
        *_BASE_COLS(),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, comment="客户ID"),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=False, comment="计划跟进日期"),
        sa.Column("completed_date", sa.DateTime(timezone=True), nullable=True, comment="实际完成日期"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", comment="状态"),
        sa.Column("content", sa.Text, nullable=True, comment="跟进内容"),
        sa.Column("result", sa.Text, nullable=True, comment="跟进结果"),
    )
    op.create_index("ix_customer_followups_customer", "customer_followups", ["customer_id"])

    # ============================================================
    # 5. training_scenarios — 训练场景
    # ============================================================
    op.create_table(
        "training_scenarios",
        *_BASE_COLS(),
        sa.Column("title", sa.String(200), nullable=False, comment="场景标题"),
        sa.Column("description", sa.Text, nullable=False, comment="场景描述"),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="medium", comment="难度"),
        sa.Column("customer_persona", JSONB, nullable=True, server_default="{}", comment="客户人设"),
        sa.Column("product_focus", sa.String(100), nullable=True, comment="聚焦产品类型"),
        sa.Column("sales_stage", sa.String(50), nullable=True, comment="销售阶段"),
        sa.Column("evaluation_criteria", JSONB, nullable=True, server_default="{}", comment="评估标准"),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="10", comment="建议时长"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true", comment="是否启用"),
    )
    op.create_index("ix_training_scenarios_difficulty", "training_scenarios", ["difficulty"])

    # ============================================================
    # 6. training_sessions — 训练会话
    # ============================================================
    op.create_table(
        "training_sessions",
        *_BASE_COLS(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID"),
        sa.Column("scenario_id", UUID(as_uuid=True), sa.ForeignKey("training_scenarios.id", ondelete="SET NULL"), nullable=True, comment="场景ID"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="状态"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="完成时间"),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0", comment="消息数量"),
    )
    op.create_index("ix_training_sessions_user", "training_sessions", ["user_id"])
    op.create_index("ix_training_sessions_scenario", "training_sessions", ["scenario_id"])

    # ============================================================
    # 7. training_messages — 训练消息
    # ============================================================
    op.create_table(
        "training_messages",
        *_BASE_COLS(),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False, comment="会话ID"),
        sa.Column("role", sa.String(20), nullable=False, comment="角色"),
        sa.Column("content", sa.Text, nullable=False, comment="消息内容"),
        sa.Column("score", sa.Float, nullable=True, comment="评分"),
        sa.Column("coaching_hint", JSONB, nullable=True, server_default="{}", comment="辅导提示"),
    )
    op.create_index("ix_training_messages_session", "training_messages", ["session_id"])

    # ============================================================
    # 8. training_scores — 训练评分
    # ============================================================
    op.create_table(
        "training_scores",
        *_BASE_COLS(),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False, unique=True, comment="会话ID"),
        sa.Column("total_score", sa.Float, nullable=False, comment="总分"),
        sa.Column("product_accuracy", sa.Float, nullable=False, comment="产品准确性"),
        sa.Column("empathy", sa.Float, nullable=False, comment="客户共情"),
        sa.Column("closing_action", sa.Float, nullable=False, comment="促单动作"),
        sa.Column("strengths", JSONB, nullable=True, server_default="[]", comment="优势列表"),
        sa.Column("weaknesses", JSONB, nullable=True, server_default="[]", comment="不足列表"),
        sa.Column("recommendations", JSONB, nullable=True, server_default="[]", comment="改进建议"),
    )

    # ============================================================
    # 9. conversations — AI 对话
    # ============================================================
    op.create_table(
        "conversations",
        *_BASE_COLS(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID"),
        sa.Column("title", sa.String(500), nullable=True, comment="对话标题"),
        sa.Column("type", sa.String(30), nullable=False, server_default="product_qa", comment="对话类型"),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, comment="关联客户ID"),
        sa.Column("context", JSONB, nullable=True, server_default="{}", comment="对话上下文"),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0", comment="消息数量"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="状态"),
    )
    op.create_index("ix_conversations_user", "conversations", ["user_id"])
    op.create_index("ix_conversations_type", "conversations", ["type"])

    # ============================================================
    # 10. messages — 对话消息
    # ============================================================
    op.create_table(
        "messages",
        *_BASE_COLS(),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, comment="对话ID"),
        sa.Column("role", sa.String(20), nullable=False, comment="发送者角色"),
        sa.Column("content", sa.Text, nullable=False, comment="消息内容"),
        sa.Column("content_type", sa.String(20), nullable=False, server_default="text", comment="内容类型"),
        sa.Column("token_count", sa.Integer, nullable=True, comment="Token 数量"),
        sa.Column("model", sa.String(100), nullable=True, comment="使用的 AI 模型"),
        sa.Column("knowledge_sources", JSONB, nullable=True, server_default="[]", comment="RAG 检索来源"),
        sa.Column("compliance_check", JSONB, nullable=True, server_default="{}", comment="合规检查结果"),
        sa.Column("feedback", sa.String(20), nullable=True, comment="用户反馈"),
    )
    op.create_index("ix_messages_conversation", "messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("training_scores")
    op.drop_table("training_messages")
    op.drop_table("training_sessions")
    op.drop_table("training_scenarios")
    op.drop_table("customer_followups")
    op.drop_table("customer_interactions")
    op.drop_table("customers")
    op.drop_table("customer_tags")
