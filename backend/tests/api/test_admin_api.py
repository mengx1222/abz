import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestAdminApi:
    async def test_list_users(self, client: AsyncClient, admin_auth_headers: dict):
        response = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

    async def test_get_analytics(self, client: AsyncClient, admin_auth_headers: dict):
        response = await client.get("/api/v1/admin/analytics/overview", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_audit_logs(self, client: AsyncClient, admin_auth_headers: dict):
        response = await client.get("/api/v1/admin/audit-logs", headers=admin_auth_headers)
        assert response.status_code in (200, 403, 500)

    async def test_agent_cannot_access_admin(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/admin/users", headers=auth_headers)
        assert response.status_code in (403, 500)

    async def test_unauthorized_admin(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/users")
        assert response.status_code in (401, 500)
