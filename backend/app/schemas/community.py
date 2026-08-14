"""社区模块 Pydantic Schema。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---- Author 简要信息 ----

class AuthorBrief(BaseModel):
    id: UUID
    name: str
    avatar: str | None = None
    role: str = "agent"
    organization: str | None = None


# ---- Post 帖子 ----

class PostCreate(BaseModel):
    title: str = Field(..., max_length=200, description="标题")
    content: str = Field(..., max_length=5000, description="正文内容(Markdown)")
    category: str = Field(
        default="discussion",
        description="分类：experience/knowledge/question/discussion/script",
    )
    tags: list[str] = Field(default_factory=list, max_length=5, description="标签")


class PostUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    content: str | None = Field(None, max_length=5000)
    category: str | None = None
    tags: list[str] | None = Field(None, max_length=5)


class PostListItem(BaseModel):
    id: UUID
    title: str
    author: AuthorBrief
    category: str
    category_label: str
    summary: str | None = None
    tags: list[str] = []
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    is_pinned: bool = False
    is_recommended: bool = False
    is_liked_by_me: bool = False
    is_favorited_by_me: bool = False
    created_at: datetime


class PostDetail(PostListItem):
    content: str = ""
    ai_summary: str | None = None
    updated_at: datetime | None = None


# ---- Comment 评论 ----

class CommentCreate(BaseModel):
    content: str = Field(..., max_length=500, description="评论内容")
    parent_comment_id: UUID | None = Field(None, description="父评论ID(回复)")


class CommentAuthor(BaseModel):
    id: UUID
    name: str
    avatar: str | None = None


class CommentItem(BaseModel):
    id: UUID
    content: str
    author: CommentAuthor
    parent_comment_id: UUID | None = None
    likes_count: int = 0
    is_liked_by_me: bool = False
    replies: list["CommentItem"] = []
    created_at: datetime


# ---- Like / Favorite ----

class LikeToggleResponse(BaseModel):
    is_liked: bool
    likes_count: int


class FavoriteToggleResponse(BaseModel):
    is_favorited: bool
    favorites_count: int


# ---- AI Summary SSE ----

class AiSummaryEvent(BaseModel):
    event: str  # summary_start / token / summary_complete / error
    data: dict | None = None
