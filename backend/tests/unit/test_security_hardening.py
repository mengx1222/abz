"""ULTIMATE P1 — 生产加固回归测试。

覆盖：
P1-1: JWT sub 非合法 UUID → 401 INVALID_TOKEN（此前 500）
P1-2: 限流 key 按路由模板聚合（UUID 段 → {id}）
P1-3: rerank 401/403 不回退 cosine（抛明确错误）；5xx 回退
P1-5: DEBUG 模式下 500 也不泄露异常详情
P1-6: 密码哈希为空统一返回“手机号或密码错误”（不泄露账号存在性）
"""
import uuid

import httpx
import pytest
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.core.config import settings


def _make_request(headers: dict | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({
        "type": "http", "method": "GET", "path": "/api/v1/x",
        "headers": raw, "client": ("203.0.113.9", 12345),
        "server": ("localhost", 8000), "query_string": b"", "scheme": "http",
    })


class TestP11InvalidUuidToken:
    async def test_non_uuid_sub_returns_401(self, monkeypatch):
        """sub 非 UUID → 401 INVALID_TOKEN（不冒泡 500）。"""
        import app.core.deps as deps_mod
        monkeypatch.setattr(deps_mod, "decode_token",
                            lambda t: {"type": "access", "sub": "not-a-uuid"})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="x")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as ei:
            await deps_mod.get_current_user(_make_request(), creds, db=None)
        assert ei.value.status_code == 401
        assert ei.value.detail["code"] == "INVALID_TOKEN"


class TestP12RouteTemplateBucket:
    def test_uuid_segments_collapsed(self):
        from app.core.rate_limit import RateLimitMiddleware
        uid = str(uuid.uuid4())
        tpl = RateLimitMiddleware._route_template(
            f"/api/v1/customers/{uid}/interactions"
        )
        assert tpl == "/api/v1/customers/{id}/interactions"
        # 两个不同 UUID 聚合到同一模板（同一桶）
        uid2 = str(uuid.uuid4())
        assert RateLimitMiddleware._route_template(
            f"/api/v1/customers/{uid2}/interactions"
        ) == tpl

    def test_plain_path_unchanged(self):
        from app.core.rate_limit import RateLimitMiddleware
        assert RateLimitMiddleware._route_template("/api/v1/auth/login") == "/api/v1/auth/login"
        assert RateLimitMiddleware._route_template("/api/v1/ai/product-qa/chat") == "/api/v1/ai/product-qa/chat"


class TestP13RerankAuthNoFallback:
    def _provider(self, monkeypatch, status: int):
        from app.ai.providers.openai_provider import OpenAIProvider
        p = OpenAIProvider(api_key="k", base_url="http://x", model="m")
        req = httpx.Request("POST", "http://x/rerank")

        class _C:
            async def post(self, *a, **k):
                resp = httpx.Response(status, request=req)
                raise httpx.HTTPStatusError("err", request=req, response=resp)

        p._client = _C()
        return p

    @pytest.mark.asyncio
    async def test_401_raises(self, monkeypatch):
        p = self._provider(monkeypatch, 401)
        with pytest.raises(RuntimeError, match="鉴权失败"):
            await p.rerank("q", ["d"])

    @pytest.mark.asyncio
    async def test_403_raises(self, monkeypatch):
        p = self._provider(monkeypatch, 403)
        with pytest.raises(RuntimeError, match="鉴权失败"):
            await p.rerank("q", ["d"])

    @pytest.mark.asyncio
    async def test_500_falls_back_to_cosine(self, monkeypatch):
        p = self._provider(monkeypatch, 500)
        async def _fb(query, documents, top_k):
            return []
        monkeypatch.setattr(p, "_cosine_rerank_fallback", _fb)
        assert await p.rerank("q", ["d"]) == []


class TestP15DebugNoDetailLeak:
    async def test_debug_mode_still_masked(self, monkeypatch):
        """DEBUG=True 时 500 响应也不含异常详情（统一文案）。"""
        monkeypatch.setattr(settings, "DEBUG", True)
        from app.core.middleware import ErrorHandlerMiddleware

        async def _boom(request):
            raise ValueError("secret-internal-detail-xyz")

        mw = ErrorHandlerMiddleware.__new__(ErrorHandlerMiddleware)
        resp = await mw.dispatch(_make_request(), _boom)
        body = resp.body.decode("utf-8")
        assert "secret-internal-detail-xyz" not in body
        assert "服务器内部错误" in body
        assert resp.status_code == 500


class TestP16AuthNoExistenceLeak:
    @pytest.mark.asyncio
    async def test_empty_password_hash_unified_message(self, monkeypatch):
        """password_hash=None → “手机号或密码错误”（不泄露账号存在性）。"""
        from app.models.role import Role
        from app.models.user import User
        from app.services.auth_service import AuthService

        class _Repo:
            async def find_by_phone(self, phone):
                u = User(
                    phone=phone, name="测试", password_hash=None, status="active",
                    role_id=uuid.uuid4(), organization_id=uuid.uuid4(),
                )
                return u

        svc = AuthService(session=object())
        svc.user_repo = _Repo()
        with pytest.raises(ValueError) as ei:
            await svc._real_login("13800138000", "whatever")
        assert "手机号或密码错误" in str(ei.value)
        assert "未设置密码" not in str(ei.value)
