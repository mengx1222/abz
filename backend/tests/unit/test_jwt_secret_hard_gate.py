"""ULTIMATE P0-4 — JWT 默认弱密钥生产硬校验。

production 环境：空/默认密钥启动即抛 RuntimeError（弱密钥可伪造 JWT）。
development/demo 不受影响（保持开发便利）。
"""
import pytest

from app.core.config import settings
from app.main import lifespan

_WEAK = "change-me-to-a-random-secret-key-in-production"
_STRONG = "x" * 48


class TestJwtSecretHardGate:
    @pytest.mark.asyncio
    async def test_production_default_secret_raises(self, monkeypatch):
        """production + 默认密钥 → RuntimeError。"""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", _WEAK)
        with pytest.raises(RuntimeError):
            async with lifespan(None):
                pass

    @pytest.mark.asyncio
    async def test_production_empty_secret_raises(self, monkeypatch):
        """production + 空密钥 → RuntimeError。"""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", "")
        with pytest.raises(RuntimeError):
            async with lifespan(None):
                pass

    @pytest.mark.asyncio
    async def test_production_strong_secret_ok(self, monkeypatch):
        """production + 强密钥 → 正常启动。"""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", _STRONG)
        async with lifespan(None):
            pass

    @pytest.mark.asyncio
    async def test_development_default_secret_ok(self, monkeypatch):
        """development + 默认密钥 → 不拦截（开发便利）。"""
        monkeypatch.setattr(settings, "APP_ENV", "development")
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", _WEAK)
        async with lifespan(None):
            pass
