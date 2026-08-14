"""测试话术 API。"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestScriptApi:
    async def test_list_scripts(self, client: AsyncClient, auth_headers: dict):
        """获取话术列表。"""
        response = await client.get("/api/v1/scripts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_script_detail(self, client: AsyncClient, auth_headers: dict):
        """获取话术详情。"""
        # 先获取列表找一个 ID
        list_resp = await client.get("/api/v1/scripts", headers=auth_headers)
        scripts = list_resp.json()["data"]
        if scripts:
            sid = scripts[0]["id"]
            resp = await client.get(f"/api/v1/scripts/{sid}", headers=auth_headers)
            assert resp.status_code == 200

    async def test_check_compliance(self, client: AsyncClient, auth_headers: dict):
        """合规检查。"""
        response = await client.post("/api/v1/scripts/check-compliance", json={
            "text": "买这个保险保证有收益"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "RED"

    async def test_generate_script_sse(self, client: AsyncClient, auth_headers: dict):
        """SSE 话术生成。"""
        async with client.stream("POST", "/api/v1/scripts/generate", json={
            "customer_context": {"name": "张先生", "age": 35, "stage": "needs_analysis"},
        }, headers=auth_headers) as response:
            assert response.status_code == 200
            chunks = []
            async for line in response.aiter_lines():
                if line.strip():
                    chunks.append(line)
            # 应该至少有 connected 事件
            assert len(chunks) >= 1

    async def test_toggle_favorite(self, client: AsyncClient, auth_headers: dict):
        """收藏话术。"""
        list_resp = await client.get("/api/v1/scripts", headers=auth_headers)
        scripts = list_resp.json()["data"]
        if scripts:
            sid = scripts[0]["id"]
            resp = await client.post(f"/api/v1/scripts/{sid}/favorite", headers=auth_headers)
            assert resp.status_code == 200
