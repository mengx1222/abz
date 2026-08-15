"""AI Gateway / Provider 生产路径测试 —— Task 9。

覆盖（确定性测试，全部 Mock / Fake，不调真实 API）：
1. Mock Provider 非流式成功
2. Mock Provider 流式成功
3. OpenAIProvider 成功（chat + token usage）
4. OpenAIProvider 401 → RuntimeError（不伪造）
5. OpenAIProvider 429 → RuntimeError
6. OpenAIProvider timeout（RequestError）→ RuntimeError
7. OpenAIProvider 流式成功（SSE 解析）
8. OpenAIProvider 流式 HTTP 错误 → RuntimeError
9. 生产模式缺 API Key → 明确错误，不静默降级 Mock
10. 生产模式缺 Base URL → 明确错误，不静默降级 Mock
11. ProductQaService demo SSE 成功（message_start/token/reference_sources/message_complete）
12. ProductQaService 流式失败 → 友好错误，不崩溃
"""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.ai.gateway import AIGateway
from app.ai.providers import MockProvider, OpenAIProvider
from app.ai.service import ProductQaService
from app.core.config import settings


# ----------------------------------------------------------------------
# Fake httpx client —— 驱动 OpenAIProvider 的确定性行为
# ----------------------------------------------------------------------

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
                response=httpx.Response(self.status_code, request=req),
            )


class _FakeStreamCtx:
    def __init__(self, *, status_code: int = 200, lines: list[str] | None = None,
                 error: Exception | None = None):
        self._status_code = status_code
        self._lines = lines or []
        self._error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        if self._status_code >= 400:
            req = httpx.Request("POST", "http://test.local")
            raise httpx.HTTPStatusError(
                f"HTTP {self._status_code}", request=req,
                response=httpx.Response(self._status_code, request=req),
            )

    async def aiter_lines(self):
        if self._error:
            raise self._error
        for line in self._lines:
            yield line


class _FakeClient:
    def __init__(self, *, status_code: int = 200, payload: dict | None = None,
                 error: Exception | None = None, stream_lines: list[str] | None = None,
                 stream_error: Exception | None = None, stream_status: int = 200):
        self._status_code = status_code
        self._payload = payload or {}
        self._error = error
        self._stream_lines = stream_lines
        self._stream_error = stream_error
        self._stream_status = stream_status

    async def post(self, url: str, json: dict | None = None, timeout: float | None = None):
        if self._error:
            raise self._error
        return _FakeResp(self._status_code, self._payload)

    def stream(self, method: str, url: str, json: dict | None = None):
        return _FakeStreamCtx(
            status_code=self._stream_status,
            lines=self._stream_lines,
            error=self._stream_error,
        )

    async def aclose(self):
        pass


def _make_openai_provider(client: _FakeClient) -> OpenAIProvider:
    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://test.local/v1",
        model="test-model",
        timeout=5.0,
    )
    provider._client = client  # type: ignore[assignment]
    return provider


def _chat_payload(content: str = "你好，有什么可以帮您？",
                  prompt_tokens: int = 12, completion_tokens: int = 9) -> dict:
    return {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
        "model": "test-model",
    }


# ----------------------------------------------------------------------
# 1-2. Mock Provider
# ----------------------------------------------------------------------

async def test_mock_provider_chat_success():
    provider = MockProvider()
    result = await provider.chat(messages=[{"role": "user", "content": "介绍一下医疗险"}])
    assert result.content
    assert result.prompt_tokens >= 0
    assert result.completion_tokens >= 0


async def test_mock_provider_stream_success():
    provider = MockProvider()
    chunks = []
    async for token in provider.chat(
        messages=[{"role": "user", "content": "介绍一下重疾险"}], stream=True
    ):
        chunks.append(token)
    assert chunks
    assert "".join(chunks)


# ----------------------------------------------------------------------
# 3-8. OpenAIProvider（Fake httpx client 驱动）
# ----------------------------------------------------------------------

async def test_openai_provider_chat_success_with_usage():
    provider = _make_openai_provider(_FakeClient(payload=_chat_payload("好的。")))
    result = await provider.chat(messages=[{"role": "user", "content": "hi"}])
    assert result.content == "好的。"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 9
    assert result.model == "test-model"
    assert result.latency_ms >= 0


async def test_openai_provider_401_raises():
    provider = _make_openai_provider(
        _FakeClient(status_code=401, payload={"error": {"message": "invalid api key"}})
    )
    with pytest.raises(RuntimeError, match="401"):
        await provider.chat(messages=[{"role": "user", "content": "hi"}])


async def test_openai_provider_429_raises():
    provider = _make_openai_provider(
        _FakeClient(status_code=429, payload={"error": {"message": "rate limit"}})
    )
    with pytest.raises(RuntimeError, match="429"):
        await provider.chat(messages=[{"role": "user", "content": "hi"}])


async def test_openai_provider_timeout_raises():
    provider = _make_openai_provider(
        _FakeClient(error=httpx.ConnectTimeout("connection timed out"))
    )
    with pytest.raises(RuntimeError, match="连接失败|timeout|timed out"):
        await provider.chat(messages=[{"role": "user", "content": "hi"}])


async def test_openai_provider_invalid_response_does_not_crash():
    # 无 choices 的畸形响应 → content 为空但不抛错
    provider = _make_openai_provider(_FakeClient(payload={"unexpected": True}))
    result = await provider.chat(messages=[{"role": "user", "content": "hi"}])
    assert result.content == ""


async def test_openai_provider_stream_success():
    lines = [
        'data: {"choices":[{"delta":{"content":"你"}}]}',
        'data: {"choices":[{"delta":{"content":"好"}}]}',
        "data: [DONE]",
    ]
    provider = _make_openai_provider(_FakeClient(stream_lines=lines))
    chunks = []
    async for token in provider.chat(
        messages=[{"role": "user", "content": "hi"}], stream=True
    ):
        chunks.append(token)
    assert chunks == ["你", "好"]


async def test_openai_provider_stream_http_error_raises():
    provider = _make_openai_provider(_FakeClient(stream_status=401))
    with pytest.raises(RuntimeError, match="401"):
        async for _ in provider.chat(
            messages=[{"role": "user", "content": "hi"}], stream=True
        ):
            pass


# ----------------------------------------------------------------------
# 9-10. Gateway：生产模式缺凭据 → 明确错误，绝不静默降级 Mock
# ----------------------------------------------------------------------

async def test_gateway_production_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    monkeypatch.setattr(settings, "AI_BASE_URL", "https://api.deepseek.com")

    gw = AIGateway()
    gw._provider = None  # 强制重新初始化
    with pytest.raises(RuntimeError, match="AZB_AI_API_KEY"):
        await gw._ensure_provider()


async def test_gateway_production_missing_base_url_raises(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "AI_PROVIDER", "qwen")
    monkeypatch.setattr(settings, "AI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "AI_BASE_URL", "")

    gw = AIGateway()
    gw._provider = None
    with pytest.raises(RuntimeError, match="AZB_AI_BASE_URL"):
        await gw._ensure_provider()


async def test_gateway_mock_mode_uses_mock(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "AI_PROVIDER", "deepseek")  # 即使配置了真实 provider

    gw = AIGateway()
    gw._provider = None
    provider = await gw._ensure_provider()
    assert isinstance(provider, MockProvider)


async def test_gateway_chat_via_mock(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    gw = AIGateway()
    gw._provider = None
    result = await gw.chat(messages=[{"role": "user", "content": "你好"}])
    assert isinstance(result, type(result))
    assert result.content


# ----------------------------------------------------------------------
# 11-12. ProductQaService SSE（demo 模式，验证真实 wiring 与错误路径）
# ----------------------------------------------------------------------

def _collect(gen):
    return [json.loads(e) for e in gen]


async def test_product_qa_sse_success(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    service = ProductQaService(db=None)
    events = _collect([
        e async for e in service.chat(user=None, question="介绍一下医疗险")
    ])
    types = [ev["event"] for ev in events]
    assert "message_start" in types
    assert "token" in types
    assert "reference_sources" in types
    assert "message_complete" in types
    # SSE 顺序约束：start → ... → complete
    assert types.index("message_start") < types.index("message_complete")
    complete = next(ev for ev in events if ev["event"] == "message_complete")
    assert complete["data"]["content"]


async def test_product_qa_sse_error_friendly(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    service = ProductQaService(db=None)

    async def _boom(*args, **kwargs):
        raise RuntimeError("AI provider timeout")

    monkeypatch.setattr(service.gateway, "chat", _boom)
    events = _collect([
        e async for e in service.chat(user=None, question="介绍一下医疗险")
    ])
    types = [ev["event"] for ev in events]
    # 失败时仍完整结束（friendly error），不崩溃
    assert "message_complete" in types
    complete = next(ev for ev in events if ev["event"] == "message_complete")
    assert complete["data"]["content"]
