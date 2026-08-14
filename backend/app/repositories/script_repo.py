"""话术仓储层。"""
import uuid

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.script import Script, ScriptVersion, ScriptFavorite
from app.repositories.base import BaseRepository


class ScriptRepository(BaseRepository[Script]):
    """话术仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Script, session)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        product_type: str | None = None,
        style: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Script], int]:
        """按用户筛选话术列表。"""
        query = select(Script).where(
            Script.is_deleted == False,
            Script.created_by == user_id,
        )
        count_q = select(func.count()).select_from(Script).where(
            Script.is_deleted == False,
            Script.created_by == user_id,
        )
        if product_type:
            query = query.where(Script.product_type == product_type)
            count_q = count_q.where(Script.product_type == product_type)
        if style:
            query = query.where(Script.style == style)
            count_q = count_q.where(Script.style == style)
        if search:
            pat = f"%{search}%"
            query = query.where(Script.title.ilike(pat))
            count_q = count_q.where(Script.title.ilike(pat))

        total = (await self.session.execute(count_q)).scalar() or 0
        query = query.order_by(Script.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.execute(query)).scalars().all()), total


class ScriptVersionRepository(BaseRepository[ScriptVersion]):
    """话术版本仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(ScriptVersion, session)

    async def get_by_script(self, script_id: uuid.UUID) -> list[ScriptVersion]:
        """获取话术的所有版本。"""
        result = await self.session.execute(
            select(ScriptVersion)
            .where(ScriptVersion.script_id == script_id)
            .order_by(ScriptVersion.created_at.desc())
        )
        return list(result.scalars().all())


class ScriptFavoriteRepository(BaseRepository[ScriptFavorite]):
    """话术收藏仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(ScriptFavorite, session)

    async def toggle(self, user_id: uuid.UUID, script_id: uuid.UUID) -> bool:
        """切换收藏状态。返回 True=收藏，False=取消收藏。"""
        result = await self.session.execute(
            select(ScriptFavorite).where(
                ScriptFavorite.user_id == user_id,
                ScriptFavorite.script_id == script_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            await self.session.delete(existing)
            await self.session.flush()
            return False
        else:
            fav = ScriptFavorite(user_id=user_id, script_id=script_id)
            self.session.add(fav)
            await self.session.flush()
            return True
