"""社区相关数据模型。

包含 Post（帖子）、PostComment（评论）、PostLike（点赞）、PostFavorite（收藏）。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Post(Base):
    """社区帖子。"""

    __tablename__ = "community_posts"

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="正文内容(Markdown)")
    summary: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="摘要(自动截取或AI生成)"
    )
    category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="discussion",
        comment="分类：experience/knowledge/question/discussion/script",
    )
    tags: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment="标签列表"
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="作者ID",
    )
    views_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="浏览量"
    )
    likes_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="点赞数"
    )
    comments_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="评论数"
    )
    favorites_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="收藏数"
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", comment="是否置顶"
    )
    is_recommended: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", comment="是否推荐"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="published",
        comment="状态：pending_review/published/rejected/hidden",
    )
    ai_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI自动生成的摘要"
    )
    # 关系
    comments: Mapped[list["PostComment"]] = relationship(
        "PostComment", back_populates="post", lazy="selectin"
    )


class PostComment(Base):
    """帖子评论。"""

    __tablename__ = "community_post_comments"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="帖子ID",
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="评论者ID",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="评论内容"
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_post_comments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="父评论ID(回复)",
    )
    likes_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="点赞数"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="软删除",
    )
    # 关系
    post: Mapped["Post"] = relationship("Post", back_populates="comments")
    replies: Mapped[list["PostComment"]] = relationship(
        "PostComment",
        backref="parent_comment",
        remote_side="PostComment.id",
        lazy="selectin",
    )


class PostLike(Base):
    """帖子点赞（多对多关联表）。"""

    __tablename__ = "community_post_likes"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="帖子ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )


class PostFavorite(Base):
    """帖子收藏（多对多关联表）。"""

    __tablename__ = "community_post_favorites"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="帖子ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
