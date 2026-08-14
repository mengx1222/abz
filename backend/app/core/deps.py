import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from structlog import get_logger

from app.core.config import settings
from app.core.security import decode_token, hash_password
from app.models.user import User
from app.models.role import Role
from app.models.organization import Organization, OrgType

logger = get_logger()

# ---- Async engine & session factory ----

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：获取异步数据库会话。"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---- Redis ----

_redis_client: Optional[Redis] = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI 依赖：获取 Redis 连接。"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            logger.warning("Redis connection failed, using no-op client")
            return
    try:
        yield _redis_client
    except Exception:
        pass


# ---- Auth ----

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI 依赖：从 JWT token 中解析当前用户。"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "未提供认证令牌"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "令牌无效或已过期"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN_TYPE", "message": "令牌类型错误"},
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "令牌中缺少用户标识"},
        )

    user_id = uuid.UUID(user_id_str)
    user: User | None = None

    # 尝试从数据库查询
    try:
        result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
        user = result.scalar_one_or_none()
    except Exception as e:
        logger.debug("Database query failed in get_current_user", error=str(e))

    # 演示模式：数据库中找不到用户时，从 token 重建演示用户对象
    if user is None and settings.DEMO_MODE:
        phone = payload.get("phone", "")
        if phone == "13800138000":
            user = _build_demo_user(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "用户不存在"},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_DISABLED", "message": "用户已被禁用"},
        )

    return user


def _build_demo_user(user_id: uuid.UUID) -> User:
    """构造一个内存中的演示用户对象。"""
    now = datetime.now(timezone.utc)
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    role_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    user = User(
        id=user_id,
        phone="13800138000",
        name="林思远",
        password_hash=hash_password("888888"),
        status="active",
        demo_mode=True,
        role_id=role_id,
        organization_id=org_id,
        created_at=now,
        updated_at=now,
    )
    user.role = Role(
        id=role_id,
        code="AGENT",
        name="代理人",
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


async def require_role(allowed_roles: list[str]):
    """FastAPI 依赖工厂：校验用户角色。"""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role_code not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "权限不足"},
            )
        return current_user
    return _check
