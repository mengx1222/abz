"""Phase 3 API 验证脚本 — Production 模式 + SQLite 数据库

运行方式:
    cd /home/z/my-project/backend && .venv/bin/python -m scripts.phase3_verify
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 强制使用 SQLite + Production 模式
os.environ["AZB_DATABASE_URL"] = "sqlite+aiosqlite:///./data/abz_dev.db"
os.environ["AZB_DEMO_MODE"] = "false"
os.environ["AZB_AI_PROVIDER"] = "mock"
os.environ["AZB_DEBUG"] = "false"

from httpx import AsyncClient, ASGITransport

# 注册 SQLite 兼容类型
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
if not hasattr(SQLiteTypeCompiler, 'visit_JSONB'):
    SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON
if not hasattr(SQLiteTypeCompiler, 'visit_UUID'):
    SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "TEXT"

import sqlalchemy as sa
from app.models.base import Base
for table in Base.metadata.tables.values():
    for col in table.columns:
        tn = col.type.__class__.__name__
        if tn == "Vector":
            col.type = sa.LargeBinary()
        elif tn == "JSONB":
            col.type = sa.JSON()

# 导入 app（触发所有模型注册）
from app.main import app

BASE_URL = "http://test"

DEMO_USERS = {
    "林思远": "13800138000",
    "张伟": "13800138001",
    "李芳": "13800138002",
    "王强": "13800138003",
}


async def test_api(name, method, path, token=None, json=None, expected_status=200):
    """测试单个 API 端点。"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        resp = await client.request(method, path, headers=headers, json=json)
        status = "OK" if resp.status_code == expected_status else f"FAIL({resp.status_code})"
        body_preview = ""
        try:
            data = resp.json()
            if isinstance(data, dict):
                # 统计列表长度
                for k in ("items", "posts", "scenarios", "scripts", "notifications", "customers"):
                    if k in data and isinstance(data[k], list):
                        body_preview = f"[{len(data[k])} items]"
                        break
                if not body_preview:
                    body_preview = f"keys={list(data.keys())[:5]}"
            elif isinstance(data, list):
                body_preview = f"[{len(data)} items]"
        except Exception:
            body_preview = resp.text[:80] if resp.text else ""
        print(f"  {'✅' if resp.status_code == expected_status else '❌'} {status} {method} {path} {body_preview}")
        return resp


async def main():
    print("=" * 70)
    print("Phase 3 API Verification (Production Mode + SQLite)")
    print("=" * 70)

    # 1. Health check
    print("\n[Health & Ready]")
    await test_api("health", "GET", "/api/v1/health")
    await test_api("ready", "GET", "/api/v1/ready")

    # 2. Login (Production mode - from DB)
    print("\n[Auth - Production Login]")
    resp = await test_api("login", "POST", "/api/v1/auth/login",
                          json={"phone": "13800138000", "password": "888888"})
    if resp.status_code != 200:
        print("  ❌ Login failed! Production auth not working")
        # Fallback: check if demo mode fallback works
        print("  ℹ️  Trying with demo fallback...")
        os.environ["AZB_DEMO_MODE"] = "true"
        resp = await test_api("login_demo", "POST", "/api/v1/auth/login",
                              json={"phone": "13800138000", "password": "888888"})
        if resp.status_code != 200:
            print("  ❌ Even demo login failed!")
            return
    data = resp.json()
    # Token 在 data 字段中（统一响应格式）
    inner = data.get("data", data)
    token = inner.get("access_token")
    if not token:
        print(f"  ❌ No token in response: {data}")
        return
    print(f"  Token: {token[:20]}...")

    # 3. Get current user
    print("\n[Auth - Current User]")
    resp = await test_api("me", "GET", "/api/v1/auth/me", token=token)
    if resp.status_code == 200:
        user_data = resp.json()
        print(f"  User: {user_data.get('name')} ({user_data.get('phone')}) role={user_data.get('role_code')}")

    # 4. Business APIs
    print("\n[Dashboard]")
    await test_api("dashboard", "GET", "/api/v1/dashboard", token=token)

    print("\n[Customers]")
    await test_api("customer_list", "GET", "/api/v1/customers", token=token)

    print("\n[Scripts]")
    await test_api("script_list", "GET", "/api/v1/scripts", token=token)

    print("\n[Training]")
    await test_api("scenario_list", "GET", "/api/v1/training/scenarios", token=token)

    print("\n[Community]")
    await test_api("post_list", "GET", "/api/v1/community/posts", token=token)

    print("\n[Notifications]")
    await test_api("notif_list", "GET", "/api/v1/notifications", token=token)

    print("\n[Growth]")
    await test_api("growth_overview", "GET", "/api/v1/growth/overview", token=token)

    print("\n[Knowledge]")
    await test_api("kb_list", "GET", "/api/v1/admin/knowledge-bases", token=token)

    print("\n[Admin - Users]")
    await test_api("admin_users", "GET", "/api/v1/admin/users", token=token)

    print("\n[Admin - Analytics]")
    await test_api("admin_analytics", "GET", "/api/v1/admin/analytics/overview", token=token)

    print(f"\n{'='*70}")
    print("Verification Complete!")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
