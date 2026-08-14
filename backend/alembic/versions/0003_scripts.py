"""add_scripts_and_script_versions_tables

Revision ID: 0003_scripts
Revises: 0002_knowledge_ai
Create Date: 2025-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "0003_scripts"
down_revision: Union[str, None] = "0002_knowledge_ai"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- scripts ----
    op.create_table(
        "scripts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False, comment="话术标题"),
        sa.Column("customer_context", JSONB, nullable=True, comment="客户上下文"),
        sa.Column("style", sa.String(20), nullable=False, comment="风格"),
        sa.Column("content", sa.Text, nullable=True, comment="话术内容"),
        sa.Column("product_type", sa.String(50), nullable=True, comment="产品类型"),
        sa.Column("compliance_status", sa.String(10), nullable=False, server_default="green", comment="合规状态"),
        sa.Column("compliance_issues", JSONB, nullable=True, comment="合规检查结果"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1", comment="版本号"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", comment="状态"),
        sa.Column("favorited_count", sa.Integer, nullable=False, server_default="0", comment="收藏数"),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0", comment="使用次数"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True, comment="创建人"),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True, comment="更新人"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        # 索引
    )
    op.create_index("ix_scripts_style", "scripts", ["style"])
    op.create_index("ix_scripts_product_type", "scripts", ["product_type"])
    op.create_index("ix_scripts_compliance_status", "scripts", ["compliance_status"])
    op.create_index("ix_scripts_status", "scripts", ["status"])
    op.create_index("ix_scripts_created_by", "scripts", ["created_by"])

    # GIN 索引用于 JSONB 查询（customer_context）
    op.create_index("ix_scripts_customer_context", "scripts", ["customer_context"], postgresql_using="gin")

    # 全文搜索索引
    op.execute("""
        CREATE INDEX ix_scripts_content_fts ON scripts
        USING gin(to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, '')))
    """)

    # ---- script_versions ----
    op.create_table(
        "script_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("script_id", UUID(as_uuid=True), sa.ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False, comment="版本号"),
        sa.Column("content", sa.Text, nullable=False, comment="版本内容"),
        sa.Column("prompt_version", sa.String(50), nullable=True, comment="使用的Prompt版本"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_script_versions_script_id", "script_versions", ["script_id"])

    # ---- script_favorites（话术收藏关联表） ----
    op.create_table(
        "script_favorites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_id", UUID(as_uuid=True), sa.ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_script_favorites_user_id", "script_favorites", ["user_id"])
    op.create_index("ix_script_favorites_script_id", "script_favorites", ["script_id"])
    op.create_unique_constraint("uq_script_favorite_user_script", "script_favorites", ["user_id", "script_id"])


def downgrade() -> None:
    op.drop_table("script_favorites")
    op.drop_table("script_versions")
    op.drop_table("scripts")
