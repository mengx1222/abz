import uuid
from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from app.models.user import User
from app.models.role import Role
from app.models.organization import Organization, OrgType
from app.repositories.user_repo import UserRepository
from app.schemas.user import TokenResponse, UserOut

logger = get_logger()

# 演示账号配置 — 支持多个演示用户
DEMO_PASSWORD = "888888"

DEMO_USERS_CONFIG = {
    "13800138000": {"name": "林思远", "role_code": "AGENT",         "role_name": "代理人"},
    "13800138001": {"name": "张伟",   "role_code": "TEAM_LEADER",   "role_name": "团队长"},
    "13800138002": {"name": "李芳",   "role_code": "BRANCH_ADMIN",  "role_name": "分公司管理员"},
    "13800138003": {"name": "王强",   "role_code": "SYSTEM_ADMIN",  "role_name": "系统管理员"},
}


class AuthService:
    """认证服务。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def login(self, phone: str, password: str) -> TokenResponse:
        """用户登录。

        - 演示模式：使用虚拟演示用户
        - 正式模式：从数据库验证
        """
        if settings.DEMO_MODE:
            return await self._demo_login(phone, password)

        return await self._real_login(phone, password)

    async def _demo_login(self, phone: str, password: str) -> TokenResponse:
        """演示模式登录逻辑。"""
        if password != DEMO_PASSWORD:
            raise ValueError("密码错误")

        if phone not in DEMO_USERS_CONFIG:
            raise ValueError("手机号或密码错误")

        # 尝试从数据库查找演示用户，失败则动态构造
        user: User | None = None
        try:
            user = await self.user_repo.find_by_phone(phone)
        except Exception as e:
            logger.debug("Database query failed in demo login, using in-memory user", error=str(e))

        if user is None:
            user = self._build_demo_user(phone)

        return self._issue_tokens(user)

    @staticmethod
    def _build_demo_user(phone: str) -> User:
        """构造一个内存中的演示用户对象。"""
        config = DEMO_USERS_CONFIG.get(phone)
        if not config:
            raise ValueError(f"未知的演示用户: {phone}")

        now = datetime.now(timezone.utc)
        org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        role_id = uuid.uuid4()
        user_id = uuid.uuid4()

        user = User(
            id=user_id,
            phone=phone,
            name=config["name"],
            password_hash=hash_password(DEMO_PASSWORD),
            status="active",
            demo_mode=True,
            role_id=role_id,
            organization_id=org_id,
            created_at=now,
            updated_at=now,
        )
        user.role = Role(
            id=role_id,
            code=config["role_code"],
            name=config["role_name"],
            level=1,
            created_at=now,
            updated_at=now,
        )
        user.organization = Organization(
            id=org_id,
            name="华安保险总部",
            type=OrgType.HQ,
            created_at=now,
            updated_at=now,
        )
        return user

    async def _real_login(self, phone: str, password: str) -> TokenResponse:
        """正式模式登录逻辑。"""
        user = await self.user_repo.find_by_phone(phone)
        if user is None:
            raise ValueError("手机号或密码错误")

        if user.status != "active":
            raise ValueError("账号已被禁用")

        if user.password_hash is None:
            raise ValueError("该账号未设置密码，请联系管理员")

        if not verify_password(password, user.password_hash):
            raise ValueError("手机号或密码错误")

        # 更新最后登录时间
        await self.user_repo.update_last_login(user.id)
        await self.session.commit()

        return self._issue_tokens(user)

    def _issue_tokens(self, user: User) -> TokenResponse:
        """为用户签发 JWT token。"""
        token_data = {"sub": str(user.id), "phone": user.phone}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """使用 refresh token 刷新 access token。"""
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise ValueError("刷新令牌无效或已过期")

        if payload.get("type") != "refresh":
            raise ValueError("令牌类型错误")

        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise ValueError("令牌中缺少用户标识")

        user_id = uuid.UUID(user_id_str)

        # 演示模式下从 token 重建用户
        if settings.DEMO_MODE:
            phone = payload.get("phone", "")
            if phone in DEMO_USERS_CONFIG:
                user = self._build_demo_user(phone)
                user.id = user_id
                return self._issue_tokens(user)

        user = await self.user_repo.get_by_id_active(user_id)
        if user is None:
            raise ValueError("用户不存在")

        if user.status != "active":
            raise ValueError("账号已被禁用")

        return self._issue_tokens(user)

    def build_user_output(self, user: User) -> UserOut:
        """将 User 模型转换为输出 schema。"""
        return UserOut(
            id=user.id,
            phone=user.phone,
            name=user.name,
            avatar_url=user.avatar_url,
            role_code=user.role_code,
            role_name=user.role_name,
            organization_id=user.organization_id,
            team_id=user.team_id,
            status=user.status,
            last_login_at=user.last_login_at,
            demo_mode=user.demo_mode,
            created_at=user.created_at,
        )
