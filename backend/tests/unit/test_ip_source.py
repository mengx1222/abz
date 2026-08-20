"""ULTIMATE P0-3 — 客户端 IP 来源可信化。

默认 AZB_TRUST_PROXY=false：伪造 X-Forwarded-For / X-Real-IP 不生效（限流与审计
都以 request.client.host 为准，杜绝伪造 XFF 绕过限流）；开启后仅信任 X-Real-IP。
"""
import pytest
from starlette.requests import Request

from app.core import audit
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware


def _make_request(headers: dict, client_host: str = "203.0.113.9") -> Request:
    raw = [
        (k.lower().encode(), v.encode())
        for k, v in headers.items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/health",
        "headers": raw,
        "client": (client_host, 54321),
        "server": ("localhost", 8000),
        "query_string": b"",
        "scheme": "http",
    }
    return Request(scope)


class TestClientIpSource:
    def test_default_ignores_spoofed_xff(self, monkeypatch):
        """TRUST_PROXY=false（默认）：伪造 XFF 不生效，取真实 socket IP。"""
        monkeypatch.setattr(settings, "TRUST_PROXY", False)
        req = _make_request({"X-Forwarded-For": "6.6.6.6, 10.0.0.1"})
        mw = RateLimitMiddleware.__new__(RateLimitMiddleware)
        assert mw._get_client_ip(req) == "203.0.113.9"
        assert audit._get_client_ip(req) == "203.0.113.9"

    def test_default_ignores_spoofed_xreal_ip(self, monkeypatch):
        """TRUST_PROXY=false：伪造 X-Real-IP 同样不生效。"""
        monkeypatch.setattr(settings, "TRUST_PROXY", False)
        req = _make_request({"X-Real-IP": "7.7.7.7"})
        mw = RateLimitMiddleware.__new__(RateLimitMiddleware)
        assert mw._get_client_ip(req) == "203.0.113.9"
        assert audit._get_client_ip(req) == "203.0.113.9"

    def test_trust_proxy_uses_x_real_ip(self, monkeypatch):
        """TRUST_PROXY=true：信任代理写入的 X-Real-IP。"""
        monkeypatch.setattr(settings, "TRUST_PROXY", True)
        req = _make_request({"X-Real-IP": "198.51.100.7", "X-Forwarded-For": "6.6.6.6"})
        mw = RateLimitMiddleware.__new__(RateLimitMiddleware)
        assert mw._get_client_ip(req) == "198.51.100.7"
        assert audit._get_client_ip(req) == "198.51.100.7"

    def test_no_client_host_fallback_unknown(self, monkeypatch):
        """无 client 信息时返回 unknown（不崩）。"""
        monkeypatch.setattr(settings, "TRUST_PROXY", False)
        scope = {
            "type": "http", "method": "GET", "path": "/",
            "headers": [], "query_string": b"", "scheme": "http",
        }
        req = Request(scope)
        mw = RateLimitMiddleware.__new__(RateLimitMiddleware)
        assert mw._get_client_ip(req) == "unknown"
        assert audit._get_client_ip(req) == "unknown"
