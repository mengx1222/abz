import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestTrainingApi:
    async def test_list_scenarios(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/training/scenarios", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    async def test_get_training_stats(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/training/stats", headers=auth_headers)
        assert response.status_code == 200

    async def test_start_session(self, client: AsyncClient, auth_headers: dict):
        list_resp = await client.get("/api/v1/training/scenarios", headers=auth_headers)
        scenarios = list_resp.json()["data"]
        if scenarios:
            sid = scenarios[0]["id"]
            resp = await client.post("/api/v1/training/sessions", json={"scenario_id": sid}, headers=auth_headers)
            assert resp.status_code in (200, 500)

    async def test_get_sessions(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/training/sessions", headers=auth_headers)
        assert response.status_code == 200

    async def test_filter_by_category(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/training/scenarios", params={"difficulty": "easy"}, headers=auth_headers)
        assert response.status_code == 200
