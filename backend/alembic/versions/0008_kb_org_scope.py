"""add knowledge_base organization scope (Task 17B)

Revision ID: 0008_kb_org_scope
Revises: 0007_kb_versioning_audit_enhance
Create Date: 2026-08-18

RAG 权限加固（Task 17B）：
- knowledge_bases 增加 organization_id 可空列（FK organizations.id, ON DELETE SET NULL）。
  null = 未限定组织的共享知识库（历史数据兼容，仍受 allowed_roles 角色约束）；
  已设置则检索时严格按可访问组织范围过滤（KnowledgeBase → Document → Chunk 继承）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0008_kb_org_scope"
down_revision: Union[str, None] = "0007_kb_versioning_audit_enhance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
            comment="所属组织（null=未限定组织的共享知识库，仍受角色约束）",
        ),
    )
    op.create_index("ix_knowledge_bases_organization_id", "knowledge_bases", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_bases_organization_id", table_name="knowledge_bases")
    op.drop_column("knowledge_bases", "organization_id")
