import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestCommunityApi:
    async def test_list_posts(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/community/posts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_post_detail(self, client: AsyncClient, auth_headers: dict):
        list_resp = await client.get("/api/v1/community/posts", headers=auth_headers)
        items = list_resp.json()["data"]
        if items:
            pid = items[0]["id"]
            resp = await client.get(f"/api/v1/community/posts/{pid}", headers=auth_headers)
            assert resp.status_code == 200

    async def test_toggle_like(self, client: AsyncClient, auth_headers: dict):
        list_resp = await client.get("/api/v1/community/posts", headers=auth_headers)
        items = list_resp.json()["data"]
        if items:
            pid = items[0]["id"]
            resp = await client.post(f"/api/v1/community/posts/{pid}/like", headers=auth_headers)
            assert resp.status_code == 200

    async def test_toggle_favorite(self, client: AsyncClient, auth_headers: dict):
        list_resp = await client.get("/api/v1/community/posts", headers=auth_headers)
        items = list_resp.json()["data"]
        if items:
            pid = items[0]["id"]
            resp = await client.post(f"/api/v1/community/posts/{pid}/favorite", headers=auth_headers)
            assert resp.status_code == 200

    async def test_list_comments(self, client: AsyncClient, auth_headers: dict):
        list_resp = await client.get("/api/v1/community/posts", headers=auth_headers)
        items = list_resp.json()["data"]
        if items:
            pid = items[0]["id"]
            resp = await client.get(f"/api/v1/community/posts/{pid}/comments", headers=auth_headers)
            assert resp.status_code == 200
