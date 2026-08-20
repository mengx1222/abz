"""add_audit_log_request_id

Revision ID: 0010_audit_log
Revises: 0009_kb_metadata
Create Date: 2026-08-20

补充 audit_logs 缺失的 request_id 列（模型-迁移漂移修复，Task 37）：
模型 AuditLog 声明 request_id 字段，但 0006 迁移创建 audit_logs 表时未包含该列，
按模型写入 request_id 会触发 SQL 列不存在错误。本迁移补齐列以支持审计落库。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_audit_log"
down_revision: Union[str, None] = "0009_kb_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("request_id", sa.String(36), nullable=True, comment="请求ID"),
    )


def downgrade() -> None:
    op.drop_column("audit_logs", "request_id")
