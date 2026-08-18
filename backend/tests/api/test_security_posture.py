"""Task 24 P2-1/P2-2 — 安全态势回归测试（CSRF posture + 401/403 语义契约）。

架构事实（审计证据，docs/p2-hardening-audit.md）：
- 认证 = JWT Bearer header（app/core/deps.py HTTPBearer），无 cookie 会话；
  前端 axios interceptor 设 Authorization header，token 存 localStorage（无 withCredentials）。
- CSRF 攻击依赖浏览器自动携带凭据（cookie）；Bearer header 无法被跨站请求自动附带，
  因此当前架构不存在可利用的 CSRF 漏洞 —— 不引入 CSRF 中间件（与认证架构冲突）。
- 本文件将这些架构事实固化为防御性回归测试：若未来引入 cookie 会话/CSRF token，
  或受保护端点失去 Bearer 强制，CI 会立即失败提示重新评估防护。
- 401/403 语义契约（前端解析依赖）：
  · login/refresh 失败 → 统一 ErrorResponse { success:false, error:{code,message}, request_id }
  · get_current_user 拒绝 → FastAPI HTTPException { detail:{ code, message } }
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestCsrfPosture:
    """P2-1 — CSRF 攻击面不存在（无 cookie 会话 + 写操作强制 Bearer）。"""

    async def test_login_response_never_sets_cookie(self, client: AsyncClient):
        """登录响应不得携带任何 Set-Cookie：凭据只存在于 Bearer header，浏览器不会自动附带。"""
        response = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000",
            "password": "888888",
        })
        assert response.status_code == 200
        assert "set-cookie" not in response.headers

    async def test_state_change_endpoint_requires_bearer(self, client: AsyncClient):
        """受保护的状态修改端点（POST/PUT/DELETE）无 Bearer → 401。

        证明所有写操作强制 Bearer 认证 —— 跨站表单/图片请求无法自动附带，
        CSRF 攻击面不存在。
        """
        # logout 是 POST + Depends(get_current_user) 的受保护写端点
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    async def test_protected_read_endpoint_requires_bearer(self, client: AsyncClient):
        """受保护读端点无 Bearer → 401。"""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_invalid_token_rejected(self, client: AsyncClient):
        """无效 token → 401 INVALID_TOKEN（语义契约）。"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.value"},
        )
        assert response.status_code == 401
        body = response.json()
        assert body["detail"]["code"] == "INVALID_TOKEN"

    async def test_refresh_token_type_rejected_on_protected_endpoint(self, client: AsyncClient):
        """refresh token 访问受保护端点 → 401 INVALID_TOKEN_TYPE。"""
        login_resp = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000",
            "password": "888888",
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "INVALID_TOKEN_TYPE"


class TestAuthErrorSemantics:
    """P2-2 — 401 响应格式契约（前端 getErrorMessage 解析依赖）。"""

    async def test_login_failure_returns_unified_errorresponse(self, client: AsyncClient):
        """登录失败 401 必须是统一 ErrorResponse（非裸 detail）。"""
        response = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000",
            "password": "wrong-password",
        })
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_FAILED"
        assert body["error"]["message"]
        assert "request_id" in body

    async def test_missing_token_returns_detail_contract(self, client: AsyncClient):
        """get_current_user 拒绝格式：{ detail: { code, message } }。"""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
        body = response.json()
        assert body["detail"]["code"] == "UNAUTHORIZED"
        assert body["detail"]["message"]

    async def test_refresh_invalid_token_401(self, client: AsyncClient):
        """无效 refresh token → 401 TOKEN_REFRESH_FAILED（ErrorResponse）。"""
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "not-a-valid-jwt",
        })
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "TOKEN_REFRESH_FAILED"
