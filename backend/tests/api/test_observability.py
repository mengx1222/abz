"""Task 39 — Observability & Redaction regression 测试。

覆盖（阶段 7/8）：
1. request_id 传播（X-Request-ID 响应头回显）
2. /health/detail 凭据脱敏（masked URL 无明文密码，阶段 7 redaction）
3. /ready 依赖失败 → 503 + READINESS_FAILED（结构化错误字段，M1）
4. request 结构化日志含 user_id（登录后请求，capsys 捕获）
5. AI Provider 401 → 日志 error_code=OPENAI_CHAT_AUTH 且不回显 body（M3 + redaction）
6. AI Provider 429 → 日志 error_code=OPENAI_CHAT_RATE_LIMIT
"""
import json

import httpx
import pytest
from httpx import AsyncClient

from app.ai.providers import OpenAIProvider
from app.core.config import settings

pytestmark = pytest.mark.integration


class _FakeResp:
    def __init__(self, status_code: int = 200, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload, ensure_ascii=False)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            req = httpx.Request("POST", "http://test.local")
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=req,
                response=httpx.Response(self.status_code, request=req, text=self.text),
            )


class _FakeClient:
    def __init__(self, *, status_code: int = 200, payload: dict | None = None,
                 error: Exception | None = None):
        self._status_code = status_code
        self._payload = payload or {}
        self._error = error

    async def post(self, url: str, json: dict | None = None, timeout: float | None = None):
        if self._error:
            raise self._error
        return _FakeResp(self._status_code, self._payload)

    async def aclose(self):
        pass


def _make_provider(status_code: int) -> OpenAIProvider:
    provider = OpenAIProvider(api_key="test-key", base_url="https://test.local/v1",
                              model="test-model", timeout=5.0)
    provider._client = _FakeClient(status_code=status_code,
                                   payload={"error": {"message": "invalid api key"}})  # type: ignore[assignment]
    return provider


class TestObservability:
    async def test_request_id_propagates(self, client: AsyncClient):
        """request_id 传播：请求头 X-Request-ID → 响应头回显。"""
        resp = await client.get("/api/v1/health", headers={"X-Request-ID": "obs-test-001"})
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == "obs-test-001"

    async def test_health_detail_masks_secret(self, client: AsyncClient, monkeypatch):
        """阶段 7 redaction：/health/detail 输出 masked URL，不含明文密码。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        monkeypatch.setattr(
            settings, "DATABASE_URL",
            "postgresql+asyncpg://user:supersecretpw@db.internal:5432/anzhenbao",
        )
        monkeypatch.setattr(settings, "REDIS_URL", "redis://:redispass@redis.internal:6379/0")
        resp = await client.get("/api/v1/health/detail")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert "supersecretpw" not in body["database_url_masked"]
        assert "redispass" not in body["redis_url_masked"]
        assert "****" in body["database_url_masked"]

    async def test_ready_503_on_db_failure(self, client: AsyncClient, monkeypatch):
        """M1：依赖异常 → 非 200（503）+ 结构化 error_code=READINESS_FAILED。"""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        monkeypatch.setattr(
            settings, "DATABASE_URL",
            "postgresql+asyncpg://bad:bad@127.0.0.1:1/nope",
        )
        monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
        resp = await client.get("/api/v1/ready")
        assert resp.status_code == 503, resp.text
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "READINESS_FAILED"
        assert body["data"]["status"] == "not_ready"
        assert body["data"]["checks"]["database"] == "unreachable"

    async def test_ready_200_when_dependencies_ok(self, client: AsyncClient):
        """依赖正常（demo 模式）→ 200 ready（现有行为不回归）。"""
        resp = await client.get("/api/v1/ready")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "ready"

    async def test_request_log_contains_user_id(self, client: AsyncClient, capsys):
        """M2：request 结构化日志含 user_id（登录后 get_current_user 回写 request.state.user）。"""
        login = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000", "password": "888888",
        })
        assert login.status_code == 200
        token = login.json()["data"]["access_token"]
        # logout 需要认证 → get_current_user 执行 → request.state.user 可用
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        out = capsys.readouterr().out
        assert "request" in out and "user_id" in out, "request 日志应含 user_id 字段"

    async def test_ai_error_code_auth_logged(self, capsys):
        """M3：AI 401 → 日志 error_code=OPENAI_CHAT_AUTH；不回显 body（redaction）。"""
        provider = _make_provider(401)
        with pytest.raises(RuntimeError, match="401"):
            await provider.chat(messages=[{"role": "user", "content": "hi"}])
        out = capsys.readouterr().out
        assert "OPENAI_CHAT_AUTH" in out
        assert "invalid api key" not in out, "AI 错误响应体不得写入日志（可能回显 prompt）"

    async def test_ai_error_code_rate_limit_logged(self, capsys):
        """M3：AI 429 → 日志 error_code=OPENAI_CHAT_RATE_LIMIT。"""
        provider = _make_provider(429)
        with pytest.raises(RuntimeError, match="429"):
            await provider.chat(messages=[{"role": "user", "content": "hi"}])
        out = capsys.readouterr().out
        assert "OPENAI_CHAT_RATE_LIMIT" in out
