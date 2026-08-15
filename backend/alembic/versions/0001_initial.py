"""initial_schema — 核心身份与组织表

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01

创建基础表: organizations, roles, permissions, role_permissions, users
这些表被后续迁移 0002-0004 的外键引用，必须在链首创建。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---- Base 字段辅助（与 Base 模型一致） ----
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
    # 1. roles — 角色表
    # ============================================================
    op.create_table(
        "roles",
        *_BASE_COLS(),
        sa.Column("code", sa.String(50), unique=True, nullable=False, comment="角色编码"),
        sa.Column("name", sa.String(100), nullable=False, comment="角色名称"),
        sa.Column("description", sa.String(255), nullable=True, comment="角色描述"),
        sa.Column("level", sa.Integer, nullable=False, server_default="0", comment="角色级别"),
    )

    # ============================================================
    # 3. permissions — 权限表
    # ============================================================
    op.create_table(
        "permissions",
        *_BASE_COLS(),
        sa.Column("code", sa.String(100), unique=True, nullable=False, comment="权限编码"),
        sa.Column("name", sa.String(100), nullable=False, comment="权限名称"),
        sa.Column("module", sa.String(50), nullable=True, comment="所属模块"),
        sa.Column("description", sa.String(255), nullable=True, comment="权限描述"),
    )

    # ============================================================
    # 4. role_permissions — 角色-权限多对多关联
    # ============================================================
    op.create_table(
        "role_permissions",
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", UUID(as_uuid=True), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    # ============================================================
    # 5. organizations — 组织表（自引用 parent_id）
    # ============================================================
    op.create_table(
        "organizations",
        *_BASE_COLS(),
        sa.Column("name", sa.String(200), nullable=False, comment="组织名称"),
        sa.Column("type", sa.Enum("HQ", "BRANCH", "TEAM", name="org_type"), nullable=False, server_default="TEAM", comment="组织类型"),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, comment="上级组织ID"),
    )

    # ============================================================
    # 6. users — 用户表
    # ============================================================
    op.create_table(
        "users",
        *_BASE_COLS(),
        sa.Column("phone", sa.String(20), unique=True, nullable=False, comment="手机号"),
        sa.Column("name", sa.String(100), nullable=False, comment="姓名"),
        sa.Column("password_hash", sa.String(255), nullable=True, comment="密码哈希"),
        sa.Column("avatar_url", sa.String(500), nullable=True, comment="头像URL"),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, comment="角色ID"),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, comment="所属组织ID"),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, comment="所属团队ID"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="状态"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True, comment="最后登录时间"),
        sa.Column("demo_mode", sa.Boolean, nullable=False, server_default="false", comment="是否演示用户"),
    )
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_role_id", "users", ["role_id"])
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_team_id", "users", ["team_id"])
    op.create_index("ix_users_status", "users", ["status"])


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("organizations")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.execute("DROP TYPE IF EXISTS org_type")
