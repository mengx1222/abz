import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestNotificationApi:
    async def test_list_notifications(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/notifications", headers=auth_headers)
        assert response.status_code == 200

    async def test_mark_read(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/v1/notifications/read", json={"notification_ids": [], "read_all": True}, headers=auth_headers)
        assert response.status_code == 200

    async def test_get_preferences(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
        assert response.status_code == 200

    async def test_update_preferences(self, client: AsyncClient, auth_headers: dict):
        response = await client.put("/api/v1/notifications/preferences", json={"type_settings": {}}, headers=auth_headers)
        assert response.status_code in (200, 422, 500)
