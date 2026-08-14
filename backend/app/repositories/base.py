import uuid
from typing import Any, Generic, TypeVar, Sequence

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """通用 CRUD 仓储基类。"""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        """根据主键获取单条记录（不排除软删除）。"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_active(self, id: uuid.UUID) -> ModelType | None:
        """根据主键获取单条活跃记录。"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id, self.model.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        where_clauses: list | None = None,
        order_by: Any | None = None,
    ) -> tuple[Sequence[ModelType], int]:
        """分页查询。返回 (records, total_count)。"""
        query = select(self.model).where(self.model.is_deleted == False)
        count_query = select(func.count()).select_from(self.model).where(self.model.is_deleted == False)

        if where_clauses:
            for clause in where_clauses:
                query = query.where(clause)
                count_query = count_query.where(clause)

        if order_by is not None:
            query = query.order_by(order_by)

        # 总数
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.session.execute(query)
        records = result.scalars().all()

        return records, total

    async def create(self, **kwargs: Any) -> ModelType:
        """创建记录。"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, **kwargs: Any) -> ModelType | None:
        """更新记录。"""
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await self.session.flush()
        return await self.get_by_id(id)

    async def soft_delete(self, id: uuid.UUID) -> None:
        """软删除记录。"""
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(is_deleted=True)
        )
        await self.session.flush()

    async def hard_delete(self, id: uuid.UUID) -> None:
        """物理删除记录。"""
        await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
