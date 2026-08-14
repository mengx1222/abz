import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户仓储。"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def find_by_phone(self, phone: str) -> User | None:
        """根据手机号查找活跃用户。"""
        result = await self.session.execute(
            select(User).where(User.phone == phone, User.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def find_by_phone_any(self, phone: str) -> User | None:
        """根据手机号查找用户（包括已删除）。"""
        result = await self.session.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """更新用户最后登录时间。"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.session.flush()
