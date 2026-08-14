"""Test customer API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestCustomerApi:
    async def test_list_customers(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/customers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

    async def test_get_customer_detail(self, client: AsyncClient, auth_headers: dict):
        list_resp = await client.get("/api/v1/customers", headers=auth_headers)
        items = list_resp.json()["data"]
        if items:
            cid = items[0]["id"]
            resp = await client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
            assert resp.status_code == 200

    async def test_create_customer(self, client: AsyncClient, auth_headers: dict, sample_customer_data: dict):
        response = await client.post("/api/v1/customers", json=sample_customer_data, headers=auth_headers)
        assert response.status_code == 200

    async def test_search_customers(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/customers", params={"search": "test"}, headers=auth_headers)
        assert response.status_code == 200

    async def test_filter_by_type(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/customers", params={"customer_type": "active"}, headers=auth_headers)
        assert response.status_code == 200

    async def test_unauthorized_access(self, client: AsyncClient):
        response = await client.get("/api/v1/customers")
        assert response.status_code in (401, 403, 500)
