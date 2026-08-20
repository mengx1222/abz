from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.audit import record_audit_log
from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.schemas.common import SuccessResponse, ErrorResponse, ErrorDetail
from app.schemas.user import UserLogin, TokenResponse, UserOut, RefreshRequest
from app.services.auth_service import AuthService

logger = get_logger()
router = APIRouter()


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="用户登录",
    responses={
        401: {"model": ErrorResponse, "description": "认证失败"},
    },
)
async def login(
    body: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """用户登录，返回 JWT token。

    - 演示模式：手机号 13800138000 / 密码 888888
    - 正式模式：验证数据库中的用户凭证
    """
    request_id = getattr(request.state, "request_id", None)
    auth_service = AuthService(db)

    # 支持 verification_code（演示模式）或 password（正式模式）
    credential = body.password or body.verification_code or ""
    try:
        token_resp = await auth_service.login(body.phone, credential)
    except ValueError as e:
        logger.warning("login_failed", phone=body.phone, reason=str(e))
        await record_audit_log(
            action="login", resource_type="auth",
            description=f"登录失败: {body.phone} ({e})", status="failure", request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                error=ErrorDetail(code="AUTH_FAILED", message=str(e)),
                request_id=request_id,
            ).model_dump(),
        )

    logger.info("login_success", phone=body.phone)
    try:
        _payload = decode_token(token_resp.access_token)
        _user_id = _payload.get("sub")
    except Exception:
        _user_id = None
    await record_audit_log(
        user_id=_user_id, action="login", resource_type="auth",
        description=f"用户登录: {body.phone}", status="success", request_id=request_id,
    )
    return SuccessResponse(data=token_resp, request_id=request_id)


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="刷新令牌",
    responses={
        401: {"model": ErrorResponse, "description": "令牌无效"},
    },
)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """使用 refresh token 获取新的 access token。"""
    request_id = getattr(request.state, "request_id", None)
    auth_service = AuthService(db)

    try:
        token_resp = await auth_service.refresh_access_token(body.refresh_token)
    except ValueError as e:
        logger.warning("refresh_failed", reason=str(e))
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                error=ErrorDetail(code="TOKEN_REFRESH_FAILED", message=str(e)),
                request_id=request_id,
            ).model_dump(),
        )

    return SuccessResponse(data=token_resp, request_id=request_id)


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="用户登出",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """用户登出（当前仅返回成功，后续可加入 token 黑名单）。"""
    request_id = getattr(request.state, "request_id", None)
    logger.info("user_logout", user_id=str(current_user.id))
    return SuccessResponse(data={"message": "已登出"}, request_id=request_id)


@router.get(
    "/me",
    response_model=SuccessResponse[UserOut],
    summary="获取当前用户信息",
    responses={
        401: {"model": ErrorResponse, "description": "未认证"},
    },
)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[UserOut]:
    """获取当前登录用户的详细信息。"""
    request_id = getattr(request.state, "request_id", None)

    user_out = UserOut.model_validate(current_user)
    return SuccessResponse(data=user_out, request_id=request_id)
