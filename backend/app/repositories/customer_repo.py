"""客户仓储层。"""
import uuid

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerInteraction, CustomerFollowup, CustomerTag
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """客户仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(Customer, session)

    async def search_list(
        self,
        page: int = 1,
        page_size: int = 20,
        customer_type: str | None = None,
        current_stage: str | None = None,
        intention_level: int | None = None,
        tag: str | None = None,
        search: str | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> tuple[list[Customer], int]:
        """带筛选的客户列表查询。"""
        query = select(Customer).where(Customer.is_deleted == False)
        count_query = select(Customer.id).where(Customer.is_deleted == False)

        if customer_type:
            query = query.where(Customer.customer_type == customer_type)
            count_query = count_query.where(Customer.customer_type == customer_type)
        if current_stage:
            query = query.where(Customer.current_stage == current_stage)
            count_query = count_query.where(Customer.current_stage == current_stage)
        if intention_level is not None:
            query = query.where(Customer.intention_level == intention_level)
            count_query = count_query.where(Customer.intention_level == intention_level)
        if organization_id:
            query = query.where(Customer.organization_id == organization_id)
            count_query = count_query.where(Customer.organization_id == organization_id)
        if tag:
            # JSONB 包含匹配
            query = query.where(Customer.tags.contains([tag]))
            count_query = count_query.where(Customer.tags.contains([tag]))
        if search:
            pattern = f"%{search}%"
            search_filter = or_(
                Customer.name.ilike(pattern),
                Customer.phone.ilike(pattern),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # 总数
        from sqlalchemy import func
        total_sub = count_query.subquery()
        total_result = await self.session.execute(select(func.count()).select_from(total_sub))
        total = total_result.scalar() or 0

        # 排序 + 分页
        query = query.order_by(Customer.updated_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.session.execute(query)
        records = list(result.scalars().all())

        return records, total


class CustomerInteractionRepository(BaseRepository[CustomerInteraction]):
    """客户互动记录仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(CustomerInteraction, session)


class CustomerFollowupRepository(BaseRepository[CustomerFollowup]):
    """客户跟进任务仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(CustomerFollowup, session)
