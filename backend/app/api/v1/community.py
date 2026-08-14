"""社区 API 路由。

端点：
  GET  /community/posts              - 帖子列表
  GET  /community/posts/:id          - 帖子详情
  POST /community/posts              - 发布帖子
  PUT  /community/posts/:id          - 编辑帖子
  DELETE /community/posts/:id         - 删除帖子
  POST /community/posts/:id/like     - 点赞/取消点赞
  POST /community/posts/:id/favorite - 收藏/取消收藏
  GET  /community/posts/:id/comments - 评论列表
  POST /community/posts/:id/comments - 发表评论
  GET  /community/favorites          - 我的收藏
  GET  /community/posts/:id/ai-summary  - AI摘要(SSE)
"""
import uuid

from fastapi import APIRouter, Depends, Query, Response
from structlog import get_logger

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.community import (
    CommentCreate,
    CommentItem,
    FavoriteToggleResponse,
    LikeToggleResponse,
    PostCreate,
    PostDetail,
    PostListItem,
    PostUpdate,
)
from app.services.community_service import get_community_service

logger = get_logger()
router = APIRouter()


@router.get("/posts", summary="社区帖子列表")
async def list_posts(
    keyword: str | None = Query(None, description="搜索标题和内容"),
    category: str | None = Query(None, description="分类筛选"),
    tags: str | None = Query(None, description="标签筛选(逗号分隔)"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    items, total = await service.list_posts(
        keyword=keyword,
        category=category,
        tags=tag_list,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        user_id=current_user.id,
    )
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/favorites", summary="我的收藏")
async def my_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    items, total = await service.my_favorites(
        user_id=current_user.id, page=page, page_size=page_size
    )
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/posts/{post_id}", summary="帖子详情")
async def get_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    post = await service.get_post(post_id, user_id=current_user.id)
    if post is None:
        return SuccessResponse(data=None)
    return SuccessResponse(data=post)


@router.post("/posts", summary="发布帖子", status_code=201)
async def create_post(
    data: PostCreate,
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    # 找到用户手机号
    from app.services.auth_service import DEMO_USERS_CONFIG
    phone = "13800138000"
    for p, cfg in DEMO_USERS_CONFIG.items():
        if cfg["name"] == current_user.name:
            phone = p
            break
    result = await service.create_post(data, author_id=current_user.id, author_phone=phone)
    return SuccessResponse(data=result)


@router.put("/posts/{post_id}", summary="编辑帖子")
async def update_post(
    post_id: str,
    data: PostUpdate,
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    result = await service.update_post(post_id, data, user_id=current_user.id)
    if result is None:
        return SuccessResponse(data=None)
    return SuccessResponse(data=result)


@router.delete("/posts/{post_id}", summary="删除帖子")
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    ok = await service.delete_post(post_id)
    if not ok:
        return SuccessResponse(data=None)
    return SuccessResponse(data={"deleted": True})


@router.post("/posts/{post_id}/like", summary="点赞/取消点赞")
async def toggle_like(
    post_id: str,
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    result = await service.toggle_like(post_id, current_user.id)
    if result is None:
        return SuccessResponse(data=None)
    return SuccessResponse(data=result)


@router.post("/posts/{post_id}/favorite", summary="收藏/取消收藏")
async def toggle_favorite(
    post_id: str,
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    result = await service.toggle_favorite(post_id, current_user.id)
    if result is None:
        return SuccessResponse(data=None)
    return SuccessResponse(data=result)


@router.get("/posts/{post_id}/comments", summary="帖子评论列表")
async def list_comments(
    post_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    items, total = await service.list_comments(
        post_id, page=page, page_size=page_size, user_id=current_user.id
    )
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.post("/posts/{post_id}/comments", summary="发表评论", status_code=201)
async def add_comment(
    post_id: str,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    from app.services.auth_service import DEMO_USERS_CONFIG
    phone = "13800138000"
    for p, cfg in DEMO_USERS_CONFIG.items():
        if cfg["name"] == current_user.name:
            phone = p
            break
    result = await service.add_comment(post_id, data, author_id=current_user.id, author_phone=phone)
    if result is None:
        return SuccessResponse(data=None)
    return SuccessResponse(data=result)


@router.get("/posts/{post_id}/ai-summary", summary="AI摘要(SSE流式)")
async def ai_summary(
    post_id: str,
    current_user: User = Depends(get_current_user),
):
    service = get_community_service()
    return Response(
        content=service.generate_ai_summary(post_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
