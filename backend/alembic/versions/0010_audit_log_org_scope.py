"""Add organization_id to audit_logs (org-scoped audit queries, Task 37).

Revision ID: 0010_audit_log_org_scope
Revises: 0009_kb_metadata
Create Date: 2026-08-20

组织范围隔离：审计日志查询需按操作人所属组织过滤（BRANCH_ADMIN/HQ_ADMIN 只见
本机构+子机构），因此 audit_logs 需要固化 organization_id。
无 FK：审计行独立于组织生命周期，组织删除不阻塞、不清空历史审计。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0010_audit_log_org_scope"
down_revision: Union[str, None] = "0009_kb_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # audit_logs 增加 organization_id（操作人所属组织，审计时固化）
    op.add_column(
        "audit_logs",
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            nullable=True,
            comment="操作人所属组织ID（审计时固化）",
        ),
    )
    op.create_index(
        "ix_audit_logs_organization_id", "audit_logs", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_organization_id", table_name="audit_logs")
    op.drop_column("audit_logs", "organization_id")
