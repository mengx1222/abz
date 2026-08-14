"""测试认证 API。"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestAuthApi:
    async def test_login_demo_user(self, client: AsyncClient):
        """演示用户登录成功。"""
        response = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000",
            "password": "888888"
        })
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        """错误密码登录失败。"""
        response = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    async def test_login_unknown_phone(self, client: AsyncClient):
        """未知手机号登录失败。"""
        response = await client.post("/api/v1/auth/login", json={
            "phone": "19999999999",
            "password": "888888"
        })
        assert response.status_code == 401

    async def test_get_me(self, client: AsyncClient, auth_headers: dict):
        """获取当前用户信息。"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["phone"] == "13800138000"
        assert data["name"] == "林思远"
        assert data["demo_mode"] is True

    async def test_refresh_token(self, client: AsyncClient):
        """刷新令牌。"""
        # 先登录获取 refresh token
        login_resp = await client.post("/api/v1/auth/login", json={
            "phone": "13800138000",
            "password": "888888"
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]

        # 使用 refresh token
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access_token" in data
