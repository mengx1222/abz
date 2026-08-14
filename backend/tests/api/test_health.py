"""测试健康检查 API。"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestHealthApi:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert data["data"]["demo_mode"] is True

    async def test_ready(self, client: AsyncClient):
        response = await client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "ready"
