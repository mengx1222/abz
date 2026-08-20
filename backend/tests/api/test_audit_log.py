"""Task 37 — 审计路径 Demo 模式回归（审计落库不影响 demo 主业务）。

验证：
- login 成功/失败路径在 demo 模式照常工作（record_audit_log demo 分支仅 structlog）
- GET /admin/audit-logs demo 分支照常返回（中间件/helper 改动不破坏现有行为）
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestAuditDemoRegression:
    async def test_login_success_ok(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000", "password": "888888",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]

    async def test_login_failure_still_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000", "password": "wrong",
        })
        assert resp.status_code == 401

    async def test_audit_logs_demo_endpoint_ok(self, client: AsyncClient):
        """SYSTEM_ADMIN 演示账号（13800138003）访问 audit-logs → demo 数据照常返回。"""
        login = await client.post("/api/v1/auth/login", json={
            "phone": "13800138003", "password": "888888",
        })
        assert login.status_code == 200
        token = login.json()["data"]["access_token"]
        resp = await client.get(
            "/api/v1/admin/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "pagination" in body
        assert isinstance(body["data"], list) and len(body["data"]) > 0

    async def test_logout_with_bearer_ok(self, client: AsyncClient):
        """POST 写路径（logout）经中间件审计后照常 200（demo 分支不触碰 DB）。"""
        login = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000", "password": "888888",
        })
        token = login.json()["data"]["access_token"]
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
