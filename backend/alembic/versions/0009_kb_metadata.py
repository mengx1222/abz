"""add knowledge_base metadata column (Task 21)

Revision ID: 0009_kb_metadata
Revises: 0008_kb_org_scope
Create Date: 2026-08-18

Knowledge Base 管理 Production 化（Task 21）：
- knowledge_bases 增加 metadata JSONB 可空列，支持创建/更新时携带扩展元数据
  （与 Document/DocumentChunk 的 metadata 语义一致）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0009_kb_metadata"
down_revision: Union[str, None] = "0008_kb_org_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "metadata",
            JSONB,
            nullable=True,
            comment="扩展元数据（Task 21：创建/更新时携带）",
        ),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "metadata")
