"""全局测试 fixtures。"""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# 在导入 app 之前设置环境变量
os.environ["AZB_DEMO_MODE"] = "true"
os.environ["AZB_DEBUG"] = "false"
os.environ["AZB_DATABASE_URL"] = "sqlite+aiosqlite:///data/test.db"
os.environ["AZB_APP_ENV"] = "testing"

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """异步 HTTP 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def demo_token(client: AsyncClient):
    """获取 Demo 代理人 Token (AGENT 角色)。"""
    response = await client.post("/api/v1/auth/login", json={
        "phone": "13800138000",
        "password": "888888"
    })
    assert response.status_code == 200
    data = response.json()["data"]
    return data["access_token"]


@pytest_asyncio.fixture
async def auth_headers(demo_token: str):
    """认证请求头（代理人）。"""
    return {"Authorization": f"Bearer {demo_token}"}


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient):
    """获取管理员 Demo Token (TEAM_LEADER 角色)。"""
    response = await client.post("/api/v1/auth/login", json={
        "phone": "13800138001",
        "password": "888888"
    })
    assert response.status_code == 200
    data = response.json()["data"]
    return data["access_token"]


@pytest_asyncio.fixture
async def admin_auth_headers(admin_token: str):
    """管理员认证请求头（TEAM_LEADER）。"""
    return {"Authorization": f"Bearer {admin_token}"}
