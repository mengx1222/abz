"""Add finish_reason to messages (conversation persistence, ULTIMATE P0-2).

Revision ID: 0011_message_finish_reason
Revises: 0010_audit_log_org_scope
Create Date: 2026-08-20

生产会话历史持久化：助手消息需记录结束原因（stop / refused / error），
供会话详情展示与后续审计。列可空，历史行不受影响。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011_message_finish_reason"
down_revision: Union[str, None] = "0010_audit_log_org_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "finish_reason",
            sa.String(20),
            nullable=True,
            comment="结束原因: stop / refused / error",
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "finish_reason")
