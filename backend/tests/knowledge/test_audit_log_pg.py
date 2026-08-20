"""Task 37 — Audit Log 持久化测试（backend-pg，真实 PostgreSQL + pgvector）。

覆盖（Task 37 Phase 4）：
1. 操作成功生成日志（KB create API → audit 落库，user_id/resource_id/metadata 正确）
2. resource_id 正确（知识库 ID 写入 audit_logs.resource_id）
3. user_id 正确（操作人 ID 写入 audit_logs.user_id）
4. metadata 保存（detail JSONB）
5. 删除资源后 audit 仍存在（audit_logs 不随业务资源级联删除）
6. Repository create/list/query_by_user/query_by_resource + 过滤分页
7. GET /admin/audit-logs 生产分支返回真实审计数据

通过环境变量 AZB_TEST_DATABASE_URL 指定真实 PostgreSQL（含 pgvector），
未设置时整个模块跳过（CI backend-pg job 提供）。
"""
import os
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import audit as audit_module
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.main import app
from app.models import Base, Organization, Role, User
from app.models.audit_log import AuditLog
from app.models.organization import OrgType
from app.repositories.audit_log_repository import AuditLogRepository

PG_URL = os.environ.get("AZB_TEST_DATABASE_URL", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not PG_URL, reason="AZB_TEST_DATABASE_URL not set"),
]


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(PG_URL, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture(autouse=True)
async def _production_mode(monkeypatch):
    """conftest 默认 DEMO_MODE=true；审计落库必须走真实生产分支。"""
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")


async def _seed_user(
    session: AsyncSession,
    role_code: str = "AGENT",
    org: Organization | None = None,
) -> User:
    """创建隔离组织/角色/用户（随机后缀），返回用户。org 可传入复用（同组织多用户）。"""
    suffix = uuid.uuid4().hex[:6]
    if org is None:
        org = Organization(name=f"审计组织-{suffix}", type=OrgType.BRANCH)
        session.add(org)
        await session.flush()
    # get-or-create：CI seed 步骤已创建标准角色（code 唯一），复用避免冲突
    role = (
        await session.execute(select(Role).where(Role.code == role_code))
    ).scalar_one_or_none()
    if role is None:
        role = Role(code=role_code, name=role_code, level=1)
        session.add(role)
        await session.flush()
    user = User(
        id=uuid.uuid4(),
        phone="17" + str(uuid.uuid4().int)[:11],
        name="审计测试员",
        password_hash=None,
        role_id=role.id,
        organization_id=org.id,
        status="active",
        demo_mode=False,
    )
    user.role = role
    user.organization = org
    session.add(user)
    await session.commit()
    return user


@pytest_asyncio.fixture
async def api(session):
    """API 客户端（override get_db → 测试 session；get_current_user 按用例设置）。"""

    async def _get_db():
        yield session

    async def _current_user():
        return None

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = _current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestAuditLogRepository:
    async def test_create_and_query(self, session: AsyncSession):
        """create_log + list_logs：字段正确（user_id/resource_id/detail metadata）。"""
        user = await _seed_user(session)
        repo = AuditLogRepository(session)
        log = await repo.create_log(
            user_id=user.id,
            action="test.action",
            resource_type="system",
            resource_id=user.id,
            description="测试审计",
            detail={"key": "value", "nested": [1, 2]},
            ip_address="127.0.0.1",
            request_id="req-test-1",
        )
        await session.commit()
        assert log.id is not None
        assert log.user_id == user.id
        assert log.resource_id == user.id
        assert log.detail == {"key": "value", "nested": [1, 2]}

        rows, total = await repo.list_logs(action="test.action")
        assert total >= 1
        assert any(r.request_id == "req-test-1" for r in rows)

    async def test_list_logs_filters_and_pagination(self, session: AsyncSession):
        """过滤（user_id/action/resource_type）+ 分页 + 倒序。"""
        user = await _seed_user(session)
        repo = AuditLogRepository(session)
        for i in range(3):
            await repo.create_log(
                user_id=user.id, action="filter.a", resource_type="knowledge_base",
                resource_id=uuid.uuid4(), description=f"行{i}",
            )
        await session.commit()

        rows, total = await repo.list_logs(user_id=str(user.id), action="filter.a")
        assert total == 3
        assert len(rows) == 3

        rows, total = await repo.list_logs(user_id=str(user.id), action="filter.a", page=1, page_size=2)
        assert total == 3
        assert len(rows) == 2
        # 同一事务内 created_at 相同（PG now() 为事务时间戳）→ 对等时间行倒序不确定，仅断言集合
        assert {r.description for r in rows} <= {"行0", "行1", "行2"}

        rows, total = await repo.query_by_user(str(user.id))
        assert total >= 3

    async def test_query_by_resource(self, session: AsyncSession):
        """query_by_resource：按资源类型+ID 查询。"""
        user = await _seed_user(session)
        resource_id = uuid.uuid4()
        repo = AuditLogRepository(session)
        await repo.create_log(user_id=user.id, action="doc.upload", resource_type="document", resource_id=resource_id, description="上传")
        await repo.create_log(user_id=user.id, action="doc.publish", resource_type="document", resource_id=resource_id, description="发布")
        await session.commit()

        rows, total = await repo.query_by_resource("document", str(resource_id))
        assert total == 2
        assert {r.action for r in rows} == {"doc.upload", "doc.publish"}


class TestAuditLogApi:
    async def _patch_audit_factory(self, session, monkeypatch):
        """审计写路径的 async_session_factory 指向测试 PG（生产分支落库）。"""
        factory = async_sessionmaker(session.bind, class_=AsyncSession, expire_on_commit=False)
        monkeypatch.setattr(audit_module, "async_session_factory", factory)
        return factory

    async def test_kb_create_writes_audit(self, session, api, monkeypatch):
        """KB create（生产）→ audit_logs 落库：user_id/resource_id/action 正确。"""
        agent = await _seed_user(session, "AGENT")
        await self._patch_audit_factory(session, monkeypatch)

        async def _cu():
            return agent
        app.dependency_overrides[get_current_user] = _cu

        resp = await api.post("/api/v1/admin/knowledge-bases", json={
            "name": "审计落库测试库", "description": "", "category": "training",
        })
        assert resp.status_code == 200, resp.text
        kb_id = resp.json()["data"]["id"]

        rows, _ = await AuditLogRepository(session).list_logs(action="create", resource_type="knowledge_base")
        hit = next((r for r in rows if str(r.resource_id) == kb_id), None)
        assert hit is not None, "KB create 未生成审计日志"
        assert hit.user_id == agent.id
        assert "审计落库测试库" in hit.description

    async def test_audit_survives_resource_delete(self, session, api, monkeypatch):
        """删除 KB 后审计记录仍存在（audit_logs 不随业务资源级联删除）。"""
        agent = await _seed_user(session, "AGENT")
        await self._patch_audit_factory(session, monkeypatch)

        async def _cu():
            return agent
        app.dependency_overrides[get_current_user] = _cu

        resp = await api.post("/api/v1/admin/knowledge-bases", json={
            "name": "删除保留审计库", "description": "", "category": "training",
        })
        assert resp.status_code == 200, resp.text
        kb_id = resp.json()["data"]["id"]

        resp = await api.delete(f"/api/v1/admin/knowledge-bases/{kb_id}")
        assert resp.status_code == 200, resp.text

        rows, _ = await AuditLogRepository(session).list_logs(action="delete", resource_type="knowledge_base")
        hit = next((r for r in rows if str(r.resource_id) == kb_id), None)
        assert hit is not None, "删除 KB 后审计记录应保留"
        assert hit.user_id == agent.id

    async def test_audit_logs_list_endpoint_returns_db_rows(self, session, api, monkeypatch):
        """GET /admin/audit-logs（生产）返回真实审计数据（同 schema，含 user_name）。"""
        admin = await _seed_user(session, "SYSTEM_ADMIN")
        await self._patch_audit_factory(session, monkeypatch)
        agent = await _seed_user(session, "AGENT")

        repo = AuditLogRepository(session)
        await repo.create_log(
            user_id=agent.id, action="custom.event", resource_type="system",
            description="列表端点验证事件",
        )
        await session.commit()

        async def _cu():
            return admin
        app.dependency_overrides[get_current_user] = _cu

        resp = await api.get("/api/v1/admin/audit-logs?action=custom.event")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "pagination" in body, "PaginatedResponse 应含 pagination"
        items = body["data"]
        assert isinstance(items, list) and len(items) >= 1, "audit-logs 生产分支应返回 DB 审计行"
        first = items[0]
        assert first["action"] == "custom.event"
        assert first["user_name"] == "审计测试员"
        assert first["user_id"] == str(agent.id)



class TestAuditLogPermission:
    """Task 37b — 组织/角色权限隔离 + 敏感字段防护。

    覆盖（验收清单 Phase 5）：
    - 角色越权：AGENT 访问 /admin/audit-logs → 403（require_role）
    - 组织越权：BRANCH_ADMIN 看不到其他组织的审计行
    - 同组织可见：BRANCH_ADMIN 可见本组织审计行
    - 管理员可见：SYSTEM_ADMIN 可见全库
    - 敏感字段不落库：中间件审计行 detail 仅 status_code，不含请求体/token/password
    """

    async def _patch_audit_factory(self, session, monkeypatch):
        factory = async_sessionmaker(session.bind, class_=AsyncSession, expire_on_commit=False)
        monkeypatch.setattr(audit_module, "async_session_factory", factory)
        return factory

    async def test_agent_gets_403(self, session, api, monkeypatch):
        """角色越权：AGENT 无权读取审计日志（require_role → 403）。"""
        org_a = Organization(name="隔离组织A-" + uuid.uuid4().hex[:6], type=OrgType.BRANCH)
        session.add(org_a)
        await session.flush()
        agent = await _seed_user(session, "AGENT", org_a)
        await session.commit()

        async def _cu():
            return agent
        app.dependency_overrides[get_current_user] = _cu

        resp = await api.get("/api/v1/admin/audit-logs")
        assert resp.status_code == 403, resp.text

    async def test_branch_admin_cannot_see_other_org(self, session, api, monkeypatch):
        """组织越权：orgA 的 BRANCH_ADMIN 看不到 orgB 的审计行（过滤式，不泄露存在性）。"""
        org_a = Organization(name="隔离组织A-" + uuid.uuid4().hex[:6], type=OrgType.BRANCH)
        org_b = Organization(name="隔离组织B-" + uuid.uuid4().hex[:6], type=OrgType.BRANCH)
        session.add_all([org_a, org_b])
        await session.flush()
        admin_a = await _seed_user(session, "BRANCH_ADMIN", org_a)
        user_b = await _seed_user(session, "AGENT", org_b)
        await session.commit()

        repo = AuditLogRepository(session)
        await repo.create_log(
            user_id=user_b.id, organization_id=org_b.id, action="org.secret",
            resource_type="system", description="org-b-only-event",
        )
        await session.commit()

        async def _cu():
            return admin_a
        app.dependency_overrides[get_current_user] = _cu

        resp = await api.get("/api/v1/admin/audit-logs?action=org.secret")
        assert resp.status_code == 200, resp.text
        items = resp.json()["data"]
        assert all("org-b-only-event" not in i["description"] for i in items),             "BRANCH_ADMIN 不应看到其他组织的审计行"

    async def test_branch_admin_sees_own_org(self, session, api, monkeypatch):
        """同组织可见：orgA 的 BRANCH_ADMIN 能看到本组织审计行。"""
        org_a = Organization(name="隔离组织A-" + uuid.uuid4().hex[:6], type=OrgType.BRANCH)
        session.add(org_a)
        await session.flush()
        admin_a = await _seed_user(session, "BRANCH_ADMIN", org_a)
        user_a = await _seed_user(session, "AGENT", org_a)
        await session.commit()

        repo = AuditLogRepository(session)
        await repo.create_log(
            user_id=user_a.id, organization_id=org_a.id, action="org.local",
            resource_type="system", description="org-a-visible-event",
        )
        await session.commit()

        async def _cu():
            return admin_a
        app.dependency_overrides[get_current_user] = _cu

        resp = await api.get("/api/v1/admin/audit-logs?action=org.local")
        assert resp.status_code == 200, resp.text
        items = resp.json()["data"]
        assert any("org-a-visible-event" in i["description"] for i in items),             "BRANCH_ADMIN 应看到本组织审计行"

    async def test_system_admin_sees_all_orgs(self, session, api, monkeypatch):
        """管理员可见：SYSTEM_ADMIN 能看到所有组织的审计行。"""
        org_a = Organization(name="隔离组织A-" + uuid.uuid4().hex[:6], type=OrgType.BRANCH)
        org_b = Organization(name="隔离组织B-" + uuid.uuid4().hex[:6], type=OrgType.BRANCH)
        session.add_all([org_a, org_b])
        await session.flush()
        sysadmin = await _seed_user(session, "SYSTEM_ADMIN", org_a)
        user_b = await _seed_user(session, "AGENT", org_b)
        await session.commit()

        repo = AuditLogRepository(session)
        await repo.create_log(
            user_id=user_b.id, organization_id=org_b.id, action="org.global",
            resource_type="system", description="org-b-global-event",
        )
        await session.commit()

        async def _cu():
            return sysadmin
        app.dependency_overrides[get_current_user] = _cu

        resp = await api.get("/api/v1/admin/audit-logs?action=org.global")
        assert resp.status_code == 200, resp.text
        items = resp.json()["data"]
        assert any("org-b-global-event" in i["description"] for i in items),             "SYSTEM_ADMIN 应看到所有组织审计行"

    async def test_sensitive_fields_not_persisted(self, session, api, monkeypatch):
        """敏感字段不落库：中间件审计行 detail 仅 status_code，不含请求体/token/password。"""
        org_a = Organization(name="隔离组织A-" + uuid.uuid4().hex[:6], type=OrgType.BRANCH)
        session.add(org_a)
        await session.flush()
        agent = await _seed_user(session, "AGENT", org_a)
        await session.commit()
        await self._patch_audit_factory(session, monkeypatch)

        async def _cu():
            return agent
        app.dependency_overrides[get_current_user] = _cu

        resp = await api.post("/api/v1/admin/knowledge-bases", json={
            "name": "敏感字段测试库",
            "description": "说明含 password=jwt-secret 字样用于验证不落库",
            "category": "training",
        })
        assert resp.status_code == 200, resp.text

        rows, _ = await AuditLogRepository(session).list_logs(resource_type="knowledge_base")
        mw = [r for r in rows if r.action.startswith("post.")]
        assert mw, "中间件应产生 post. 审计行"
        for r in mw:
            assert r.detail == {"status_code": 200}, "detail 应仅含 status_code: %r" % (r.detail,)
            desc = (r.description or "").lower()
            assert "password" not in desc
            assert "jwt" not in desc
            assert "token" not in desc
            assert "secret" not in desc
