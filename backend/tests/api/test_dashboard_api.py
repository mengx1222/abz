"""Test dashboard API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestDashboardApi:
    async def test_get_dashboard(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert response.status_code == 200

    async def test_today_stats_and_suggestions_have_action_url(self, client: AsyncClient, auth_headers: dict):
        """工作台「今日工作 / AI 今日建议」卡片可点：每个条目都带 action_url（跳转目标）。

        dashboard 接口直接返回 DashboardOverview（无 data 包裹）。
        """
        response = await client.get("/api/v1/dashboard", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        for stat in body["today_stats"]:
            assert stat["action_url"], f"今日工作缺少跳转目标: {stat['label']}"
        for s in body["ai_suggestions"]:
            assert s["action_url"], f"AI 建议缺少跳转目标: {s['title']}"
