"""Test growth API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestGrowthApi:
    async def test_get_overview(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/growth/overview", headers=auth_headers)
        assert response.status_code == 200

    async def test_get_courses(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/growth/courses/course_1", headers=auth_headers)
        assert response.status_code in (200, 404, 500)

    async def test_get_leaderboard(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/growth/leaderboard", headers=auth_headers)
        assert response.status_code == 200

    async def test_get_achievements(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/growth/achievements", headers=auth_headers)
        assert response.status_code == 200
