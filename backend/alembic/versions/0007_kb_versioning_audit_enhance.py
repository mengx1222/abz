"""add kb versioning + document effective dates + audit enhance

Revision ID: 0007_kb_versioning_audit_enhance
Revises: 0006_notification_growth_audit
Create Date: 2025-03-16

为知识库添加版本管理（生效/失效日期）、文档版本链、审计日志增强字段。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0007_kb_versioning_audit_enhance"
down_revision: Union[str, None] = "0006_notification_growth_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # 1. knowledge_bases 表增强
    # ============================================================
    op.add_column("knowledge_bases",
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True, comment="生效日期"),
    )
    op.add_column("knowledge_bases",
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True, comment="失效日期"),
    )
    op.add_column("knowledge_bases",
        sa.Column("created_by", UUID(as_uuid=True), nullable=True, comment="创建人"),
    )

    # ============================================================
    # 2. documents 表增强
    # ============================================================
    op.add_column("documents",
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True, comment="生效日期"),
    )
    op.add_column("documents",
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True, comment="失效日期"),
    )
    op.add_column("documents",
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1", comment="版本号"),
    )
    op.add_column("documents",
        sa.Column("previous_version_id", UUID(as_uuid=True), nullable=True, comment="上一版本文档ID"),
    )

    # ============================================================
    # 3. audit_logs 表增强
    # ============================================================
    # ip_address 和 user_agent 已在 0006 迁移中创建，仅添加 request_id
    op.add_column("audit_logs",
        sa.Column("request_id", sa.String(36), nullable=True, comment="请求ID"),
    )


def downgrade() -> None:
    # 移除 audit_logs 增强字段
    op.drop_column("audit_logs", "request_id")

    # 移除 documents 增强字段
    op.drop_column("documents", "previous_version_id")
    op.drop_column("documents", "version_number")
    op.drop_column("documents", "expiry_date")
    op.drop_column("documents", "effective_date")

    # 移除 knowledge_bases 增强字段
    op.drop_column("knowledge_bases", "created_by")
    op.drop_column("knowledge_bases", "expiry_date")
    op.drop_column("knowledge_bases", "effective_date")
