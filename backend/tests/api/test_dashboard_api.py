"""Test dashboard API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestDashboardApi:
    async def test_get_dashboard(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert response.status_code == 200
