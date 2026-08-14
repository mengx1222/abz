"""add_community_tables

Revision ID: 0004_community
Revises: 0003_scripts
Create Date: 2025-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "0004_community"
down_revision: Union[str, None] = "0003_scripts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- community_posts ----
    op.create_table(
        "community_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False, comment="标题"),
        sa.Column("content", sa.Text, nullable=False, comment="正文内容(Markdown)"),
        sa.Column("summary", sa.String(500), nullable=True, comment="摘要"),
        sa.Column("category", sa.String(30), nullable=False, server_default="discussion",
                   comment="分类：experience/knowledge/question/discussion/script"),
        sa.Column("tags", JSONB, nullable=True, comment="标签列表"),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("views_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("likes_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("favorites_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_recommended", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="published"),
        sa.Column("ai_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )

    # 全文检索 GIN 索引
    op.execute("ALTER TABLE community_posts ADD COLUMN search_vector tsvector")
    op.execute("""
        CREATE INDEX idx_community_posts_search
        ON community_posts USING GIN(search_vector)
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION community_posts_search_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(NEW.content, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_community_posts_search_update
        BEFORE INSERT OR UPDATE OF title, content
        ON community_posts
        FOR EACH ROW EXECUTE FUNCTION community_posts_search_update()
    """)

    # ---- community_post_comments ----
    op.create_table(
        "community_post_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", UUID(as_uuid=True), sa.ForeignKey("community_posts.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False, comment="评论内容"),
        sa.Column("parent_comment_id", UUID(as_uuid=True),
                   sa.ForeignKey("community_post_comments.id", ondelete="SET NULL"),
                   nullable=True, index=True),
        sa.Column("likes_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
    )

    # ---- community_post_likes ----
    op.create_table(
        "community_post_likes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", UUID(as_uuid=True), sa.ForeignKey("community_posts.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_unique_constraint(
        "uq_post_like_user", "community_post_likes",
        ["post_id", "user_id"]
    )

    # ---- community_post_favorites ----
    op.create_table(
        "community_post_favorites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", UUID(as_uuid=True), sa.ForeignKey("community_posts.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_unique_constraint(
        "uq_post_favorite_user", "community_post_favorites",
        ["post_id", "user_id"]
    )


def downgrade() -> None:
    op.drop_table("community_post_favorites")
    op.drop_table("community_post_likes")
    op.drop_table("community_post_comments")
    op.execute("DROP TRIGGER IF EXISTS trg_community_posts_search_update ON community_posts")
    op.execute("DROP FUNCTION IF EXISTS community_posts_search_update()")
    op.drop_table("community_posts")
