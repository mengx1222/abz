"""PCRED 阶段5：Pilot Credential 分离回归测试。

验证：
1) settings.DEMO_PASSWORD 默认 888888 仅为 CI/Demo 测试凭据（可 AZB_DEMO_PASSWORD 覆盖）；
2) 模板占位密码（CHANGE_ME_*）在 seed 时 fail-fast（RuntimeError），不静默 fallback；
3) auth_service 的 DEMO_PASSWORD 与 settings 同源（代码不硬编码明文）。
"""
import pytest

from app.core.config import settings
from app.services.auth_service import DEMO_PASSWORD as AUTH_DEMO_PASSWORD
from scripts.seed import validate_pilot_password


class TestDemoPasswordDefaults:
    def test_demo_password_default_is_ci_only(self):
        """默认 888888 仅用于 CI/Demo 测试（E2E/CI-only 语义），可 env 覆盖。"""
        assert settings.DEMO_PASSWORD == "888888"
        assert AUTH_DEMO_PASSWORD == settings.DEMO_PASSWORD  # 同源

    def test_auth_service_password_from_settings(self):
        """auth_service 密码来自 settings（AZB_DEMO_PASSWORD 注入），非独立字面量。"""
        assert AUTH_DEMO_PASSWORD == settings.DEMO_PASSWORD


class TestPilotPasswordFailFast:
    def test_placeholder_password_raises(self, monkeypatch):
        """模板占位密码（CHANGE_ME_*）→ RuntimeError（BLOCKED，不 fallback 默认值）。"""
        monkeypatch.setattr(settings, "DEMO_PASSWORD", "CHANGE_ME_PILOT_STRONG_PASSWORD")
        with pytest.raises(RuntimeError, match="BLOCKED"):
            validate_pilot_password()

    def test_default_password_allowed_for_ci_demo(self, monkeypatch):
        """默认 888888（CI/Demo）不阻断 seed —— 仅为测试凭据，非 Pilot 登录密码。"""
        monkeypatch.setattr(settings, "DEMO_PASSWORD", "888888")
        validate_pilot_password()  # 不抛异常

    def test_strong_password_allowed(self, monkeypatch):
        """注入强密码（Secret 轮换后）→ 通过校验。"""
        monkeypatch.setattr(settings, "DEMO_PASSWORD", "s3cr3t-pilot-strong-pass-2026")
        validate_pilot_password()  # 不抛异常
