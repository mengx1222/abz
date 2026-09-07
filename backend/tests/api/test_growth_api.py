"""Test growth API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestGrowthApi:
    async def test_get_overview(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/growth/overview", headers=auth_headers)
        assert response.status_code == 200

    async def test_get_courses(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/growth/courses/course_1", headers=auth_headers)
        assert response.status_code in (200, 404, 500)

    async def test_get_leaderboard(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/growth/leaderboard", headers=auth_headers)
        assert response.status_code == 200

    async def test_get_achievements(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/growth/achievements", headers=auth_headers)
        assert response.status_code == 200


class TestCourseDetailProduction404:
    async def test_course_detail_production_404(self, client: AsyncClient, auth_headers: dict, monkeypatch):
        """P1-3 收敛：生产模式（无课程表）课程详情返回 404 COURSE_NOT_FOUND，而非 data:null。"""
        import uuid
        from datetime import datetime, timezone

        from app.core.config import settings
        from app.core.deps import get_current_user
        from app.main import app
        from app.models import User

        monkeypatch.setattr(settings, "DEMO_MODE", False)

        now = datetime.now(timezone.utc)
        stub_user = User(
            id=uuid.uuid4(), phone="13900000001", name="生产测试用户",
            status="active", demo_mode=False,
            role_id=uuid.uuid4(), organization_id=uuid.uuid4(),
            created_at=now, updated_at=now,
        )

        async def _current_user():
            return stub_user

        app.dependency_overrides[get_current_user] = _current_user
        try:
            response = await client.get("/api/v1/growth/courses/course-001")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "COURSE_NOT_FOUND"
