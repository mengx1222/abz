"""社区仓储层。"""
import uuid

from sqlalchemy import select, func, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Post, PostComment, PostLike, PostFavorite
from app.repositories.base import BaseRepository


class PostRepository(BaseRepository[Post]):
    """帖子仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Post, session)

    async def list_posts(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        search: str | None = None,
        sort_by: str = "latest",
    ) -> tuple[list[Post], int]:
        """帖子列表查询。"""
        query = select(Post).where(Post.is_deleted == False, Post.status == "published")
        count_q = select(func.count()).select_from(Post).where(
            Post.is_deleted == False, Post.status == "published"
        )

        if category:
            query = query.where(Post.category == category)
            count_q = count_q.where(Post.category == category)
        if search:
            pat = f"%{search}%"
            sf = or_(Post.title.ilike(pat), Post.content.ilike(pat))
            query = query.where(sf)
            count_q = count_q.where(sf)

        # 排序
        if sort_by == "most_liked":
            query = query.order_by(Post.likes_count.desc())
        elif sort_by == "most_commented":
            query = query.order_by(Post.comments_count.desc())
        else:
            query = query.order_by(Post.is_pinned.desc(), Post.updated_at.desc())

        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total

    async def list_user_favorites(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Post], int]:
        """用户收藏的帖子列表。"""
        query = (
            select(Post)
            .join(PostFavorite, PostFavorite.post_id == Post.id)
            .where(PostFavorite.user_id == user_id, Post.is_deleted == False)
            .order_by(PostFavorite.created_at.desc())
        )
        count_q = (
            select(func.count())
            .select_from(Post)
            .join(PostFavorite, PostFavorite.post_id == Post.id)
            .where(PostFavorite.user_id == user_id, Post.is_deleted == False)
        )
        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total


class PostCommentRepository(BaseRepository[PostComment]):
    """帖子评论仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(PostComment, session)

    async def list_by_post(
        self, post_id: uuid.UUID, page: int = 1, page_size: int = 50
    ) -> tuple[list[PostComment], int]:
        """获取帖子的评论列表（含回复嵌套由 Service 层组装）。"""
        query = (
            select(PostComment)
            .where(PostComment.post_id == post_id, PostComment.is_deleted == False)
            .order_by(PostComment.created_at.asc())
        )
        count_q = select(func.count()).select_from(PostComment).where(
            PostComment.post_id == post_id, PostComment.is_deleted == False
        )
        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total


class PostLikeRepository(BaseRepository[PostLike]):
    """帖子点赞仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(PostLike, session)

    async def toggle(self, user_id: uuid.UUID, post_id: uuid.UUID) -> bool:
        """切换点赞。返回 True=点赞，False=取消。"""
        result = await self.session.execute(
            select(PostLike).where(PostLike.user_id == user_id, PostLike.post_id == post_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            await self.session.delete(existing)
            await self.session.flush()
            return False
        else:
            like = PostLike(user_id=user_id, post_id=post_id)
            self.session.add(like)
            await self.session.flush()
            return True


class PostFavoriteRepository(BaseRepository[PostFavorite]):
    """帖子收藏仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(PostFavorite, session)

    async def toggle(self, user_id: uuid.UUID, post_id: uuid.UUID) -> bool:
        """切换收藏。返回 True=收藏，False=取消。"""
        result = await self.session.execute(
            select(PostFavorite).where(
                PostFavorite.user_id == user_id, PostFavorite.post_id == post_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            await self.session.delete(existing)
            await self.session.flush()
            return False
        else:
            fav = PostFavorite(user_id=user_id, post_id=post_id)
            self.session.add(fav)
            await self.session.flush()
            return True
