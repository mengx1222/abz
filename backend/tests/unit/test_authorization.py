"""测试数据权限检查（IDOR 防护）。"""
import uuid
from datetime import datetime, timezone

from app.core.authorization import DataPermissionChecker
from app.models.user import User
from app.models.role import Role
from app.models.organization import Organization, OrgType


ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
TEAM_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")
NOW = datetime.now(timezone.utc)


def _make_user(role_code="AGENT", org_id=None, team_id=None, demo_mode=True, user_id=None):
    """创建测试用户。"""
    uid = user_id or uuid.uuid4()
    oid = org_id or ORG_ID
    user = User(
        id=uid,
        phone="13800138000",
        name="测试用户",
        password_hash="",
        status="active",
        demo_mode=demo_mode,
        role_id=ROLE_ID,
        organization_id=oid,
        team_id=team_id,
        created_at=NOW,
        updated_at=NOW,
    )
    user.role = Role(
        id=ROLE_ID, code=role_code, name=role_code, level=1,
        created_at=NOW, updated_at=NOW,
    )
    user.organization = Organization(
        id=oid, name="测试组织", type=OrgType.HQ,
        created_at=NOW, updated_at=NOW,
    )
    return user


class TestDataPermissionChecker:
    def test_system_admin_all_access(self):
        user = _make_user(role_code="SYSTEM_ADMIN")
        checker = DataPermissionChecker(user)
        assert checker.can_access_customer(str(ORG_ID)) is True
        assert checker.can_access_customer(str(OTHER_ORG_ID)) is True
        assert checker.can_access_customer(None) is True

    def test_hq_admin_own_org(self):
        user = _make_user(role_code="HQ_ADMIN")
        checker = DataPermissionChecker(user)
        # Demo 模式下 _collect_child_org_ids 只返回自身
        assert checker.can_access_customer(str(ORG_ID)) is True

    def test_branch_admin_own_org(self):
        user = _make_user(role_code="BRANCH_ADMIN")
        checker = DataPermissionChecker(user)
        assert checker.can_access_customer(str(ORG_ID)) is True

    def test_team_leader_own_team(self):
        user = _make_user(role_code="TEAM_LEADER", team_id=TEAM_ID)
        checker = DataPermissionChecker(user)
        assert checker.can_access_customer(str(ORG_ID)) is True

    def test_agent_own_org_demo(self):
        """Demo 模式下 AGENT 可访问同组织客户。"""
        user = _make_user(role_code="AGENT", demo_mode=True)
        checker = DataPermissionChecker(user)
        assert checker.can_access_customer(str(ORG_ID)) is True

    def test_agent_cross_org_denied(self):
        """AGENT 不可访问跨组织客户。"""
        user = _make_user(role_code="AGENT", demo_mode=True)
        checker = DataPermissionChecker(user)
        assert checker.can_access_customer(str(OTHER_ORG_ID)) is False

    def test_none_org_id(self):
        """无组织归属数据仅系统管理员可访问。"""
        user = _make_user(role_code="AGENT")
        checker = DataPermissionChecker(user)
        assert checker.can_access_customer(None) is False

    def test_filter_accessible_orgs_system_admin(self):
        user = _make_user(role_code="SYSTEM_ADMIN")
        checker = DataPermissionChecker(user)
        assert checker.filter_accessible_org_ids() == ["__ALL__"]

    def test_filter_accessible_orgs_agent(self):
        user = _make_user(role_code="AGENT", demo_mode=True)
        checker = DataPermissionChecker(user)
        orgs = checker.filter_accessible_org_ids()
        assert str(ORG_ID) in orgs

    def test_can_manage_user_higher_role(self):
        """系统管理员可管理低层级用户。"""
        admin = _make_user(role_code="SYSTEM_ADMIN", user_id=uuid.uuid4())
        target = _make_user(role_code="AGENT", user_id=uuid.uuid4())
        checker = DataPermissionChecker(admin)
        assert checker.can_manage_user(target) is True

    def test_can_manage_user_same_role(self):
        """同级角色不能互相管理。"""
        user1 = _make_user(role_code="AGENT", user_id=uuid.uuid4())
        user2 = _make_user(role_code="AGENT", user_id=uuid.uuid4())
        checker = DataPermissionChecker(user1)
        assert checker.can_manage_user(user2) is False

    def test_cannot_manage_self(self):
        """不能管理自己。"""
        uid = uuid.uuid4()
        user = _make_user(role_code="SYSTEM_ADMIN", user_id=uid)
        checker = DataPermissionChecker(user)
        assert checker.can_manage_user(user) is False

    def test_cannot_manage_higher_role(self):
        """低层级不能管理高层级。"""
        agent = _make_user(role_code="AGENT", user_id=uuid.uuid4())
        admin = _make_user(role_code="SYSTEM_ADMIN", user_id=uuid.uuid4())
        checker = DataPermissionChecker(agent)
        assert checker.can_manage_user(admin) is False


# ==================================================================
# 生产模式（DEMO_MODE=false）P0 回归（Task 17B-Hotfix）
# 修复前：authorization.py 缺 settings 导入，_collect_child_org_ids 内
# settings.DEMO_MODE NameError → HQ/BRANCH_ADMIN 组织树解析崩溃。
# 修复后：settings.DEMO_MODE 可求值，正式分支走 org.children 递归收集。
# ==================================================================

class TestProductionModeOrgScope:
    def test_hq_admin_production_no_nameerror(self, monkeypatch):
        """P0: 生产模式 HQ_ADMIN filter_accessible_org_ids 不抛 NameError。"""
        from app.core.config import settings
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        user = _make_user(role_code="HQ_ADMIN", demo_mode=False)
        checker = DataPermissionChecker(user)
        orgs = checker.filter_accessible_org_ids()  # 修复前此处 NameError
        assert str(ORG_ID) in orgs

    def test_branch_admin_production_no_nameerror(self, monkeypatch):
        """P0: 生产模式 BRANCH_ADMIN filter_accessible_org_ids 不抛 NameError。"""
        from app.core.config import settings
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        user = _make_user(role_code="BRANCH_ADMIN", demo_mode=False)
        checker = DataPermissionChecker(user)
        orgs = checker.filter_accessible_org_ids()  # 修复前此处 NameError
        assert str(ORG_ID) in orgs

    def test_team_leader_production_no_nameerror(self, monkeypatch):
        """P0: 生产模式 TEAM_LEADER filter_accessible_org_ids 不抛 NameError。"""
        from app.core.config import settings
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        user = _make_user(role_code="TEAM_LEADER", demo_mode=False, team_id=TEAM_ID)
        checker = DataPermissionChecker(user)
        orgs = checker.filter_accessible_org_ids()  # 修复前此处 NameError
        assert str(ORG_ID) in orgs

    def test_hq_admin_production_collects_children(self, monkeypatch):
        """生产模式组织树收集：HQ_ADMIN 含本组织 + 全部子组织（RAG org scope 依赖）。"""
        from app.core.config import settings
        monkeypatch.setattr(settings, "DEMO_MODE", False)

        child1 = Organization(
            id=uuid.uuid4(), name="浦东团队", type=OrgType.TEAM,
            created_at=NOW, updated_at=NOW,
        )
        child2 = Organization(
            id=uuid.uuid4(), name="浦西团队", type=OrgType.TEAM,
            created_at=NOW, updated_at=NOW,
        )
        grandchild = Organization(
            id=uuid.uuid4(), name="浦西二组", type=OrgType.TEAM,
            created_at=NOW, updated_at=NOW,
        )
        child2.children = [grandchild]

        user = _make_user(role_code="HQ_ADMIN", demo_mode=False, org_id=ORG_ID)
        user.organization = Organization(
            id=ORG_ID, name="总部", type=OrgType.HQ,
            created_at=NOW, updated_at=NOW,
        )
        user.organization.children = [child1, child2]

        checker = DataPermissionChecker(user)
        orgs = checker.filter_accessible_org_ids()
        assert str(ORG_ID) in orgs
        assert str(child1.id) in orgs
        assert str(child2.id) in orgs
        assert str(grandchild.id) in orgs, "组织树应递归收集孙级组织"

    def test_hq_admin_production_can_access_customer(self, monkeypatch):
        """生产模式 can_access_customer 不崩溃（复用 filter_accessible_org_ids）。"""
        from app.core.config import settings
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        user = _make_user(role_code="HQ_ADMIN", demo_mode=False)
        checker = DataPermissionChecker(user)
        assert checker.can_access_customer(str(ORG_ID)) is True
        assert checker.can_access_customer(str(OTHER_ORG_ID)) is False
