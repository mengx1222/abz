#!/usr/bin/env python3
"""Phase 4-3 IDOR 防护验证脚本。

测试 DataPermissionChecker 的权限判断逻辑，
验证不同角色在不同场景下的数据访问权限是否正确。

运行方式: cd backend && python -m scripts.phase4_idor_verify
"""
import sys
import os
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------
# 模拟 User / Role / Organization 对象（不依赖数据库）
# ---------------------------------------------------------------

@dataclass
class MockRole:
    id: uuid.UUID
    code: str
    name: str
    level: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MockOrganization:
    id: uuid.UUID
    name: str
    type: str = "HQ"
    parent_id: uuid.UUID | None = None
    children: list["MockOrganization"] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MockUser:
    id: uuid.UUID
    phone: str
    name: str
    role: MockRole
    organization: MockOrganization
    team: MockOrganization | None = None
    organization_id: uuid.UUID = field(init=False)
    team_id: uuid.UUID | None = field(default=None, init=False)
    status: str = "active"
    demo_mode: bool = False

    def __post_init__(self):
        self.organization_id = self.organization.id
        self.team_id = self.team.id if self.team else None

    @property
    def role_code(self) -> str:
        return self.role.code


# ---------------------------------------------------------------
# 测试用组织/用户
# ---------------------------------------------------------------

ORG_HQ = MockOrganization(
    id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    name="华安保险总部",
    type="HQ",
)

ORG_BRANCH_A = MockOrganization(
    id=uuid.UUID("00000000-0000-0000-0000-000000000010"),
    name="华东分公司",
    type="BRANCH",
    parent_id=ORG_HQ.id,
)

ORG_BRANCH_B = MockOrganization(
    id=uuid.UUID("00000000-0000-0000-0000-000000000020"),
    name="华南分公司",
    type="BRANCH",
    parent_id=ORG_HQ.id,
)

ORG_TEAM_1 = MockOrganization(
    id=uuid.UUID("00000000-0000-0000-0000-000000000011"),
    name="华东一组",
    type="TEAM",
    parent_id=ORG_BRANCH_A.id,
)

ROLE_SYSTEM_ADMIN = MockRole(
    id=uuid.uuid4(), code="SYSTEM_ADMIN", name="系统管理员", level=100
)
ROLE_HQ_ADMIN = MockRole(
    id=uuid.uuid4(), code="HQ_ADMIN", name="总部管理员", level=80
)
ROLE_BRANCH_ADMIN = MockRole(
    id=uuid.uuid4(), code="BRANCH_ADMIN", name="分公司管理员", level=60
)
ROLE_TEAM_LEADER = MockRole(
    id=uuid.uuid4(), code="TEAM_LEADER", name="团队长", level=40
)
ROLE_AGENT = MockRole(
    id=uuid.uuid4(), code="AGENT", name="代理人", level=20
)


def make_user(name: str, role: MockRole, org: MockOrganization, team: MockOrganization | None = None, demo: bool = False) -> MockUser:
    return MockUser(
        id=uuid.uuid4(),
        phone="13800000000",
        name=name,
        role=role,
        organization=org,
        team=team,
        demo_mode=demo,
    )


# ---------------------------------------------------------------
# 测试
# ---------------------------------------------------------------

def test_filter_accessible_org_ids():
    """测试 filter_accessible_org_ids。"""
    from app.core.authorization import DataPermissionChecker

    passed = 0
    failed = 0

    def check(label: str, user: MockUser, expected: list[str]):
        nonlocal passed, failed
        checker = DataPermissionChecker(user)  # type: ignore[arg-type]
        result = checker.filter_accessible_org_ids()
        if result == expected:
            passed += 1
            print(f"  ✓ {label}")
        else:
            failed += 1
            print(f"  ✗ {label}: 期望 {expected}, 得到 {result}")

    print("\n[1] filter_accessible_org_ids")

    # SYSTEM_ADMIN → __ALL__
    u = make_user("sys", ROLE_SYSTEM_ADMIN, ORG_HQ)
    check("SYSTEM_ADMIN 返回 __ALL__", u, ["__ALL__"])

    # HQ_ADMIN → 本机构
    u = make_user("hq", ROLE_HQ_ADMIN, ORG_HQ, demo=True)
    check("HQ_ADMIN (demo) 返回本机构", u, [str(ORG_HQ.id)])

    # BRANCH_ADMIN → 本机构
    u = make_user("branch", ROLE_BRANCH_ADMIN, ORG_BRANCH_A, demo=True)
    check("BRANCH_ADMIN (demo) 返回本机构", u, [str(ORG_BRANCH_A.id)])

    # TEAM_LEADER → 本机构 + 团队
    u = make_user("leader", ROLE_TEAM_LEADER, ORG_BRANCH_A, team=ORG_TEAM_1, demo=True)
    check("TEAM_LEADER (demo) 返回 org+team", u, [str(ORG_BRANCH_A.id), str(ORG_TEAM_1.id)])

    # AGENT demo → 同机构
    u = make_user("agent", ROLE_AGENT, ORG_HQ, demo=True)
    check("AGENT (demo) 返回同机构", u, [str(ORG_HQ.id)])

    # AGENT 非demo → 同机构（正式模式也需要基础 org 过滤）
    u = make_user("agent2", ROLE_AGENT, ORG_HQ, demo=False)
    check("AGENT (非demo) 返回同机构", u, [str(ORG_HQ.id)])

    return passed, failed


def test_can_access_customer():
    """测试 can_access_customer。"""
    from app.core.authorization import DataPermissionChecker

    passed = 0
    failed = 0

    def check(label: str, user: MockUser, target_org_id: str | None, expected: bool):
        nonlocal passed, failed
        checker = DataPermissionChecker(user)  # type: ignore[arg-type]
        result = checker.can_access_customer(target_org_id)
        if result == expected:
            passed += 1
            print(f"  ✓ {label}")
        else:
            failed += 1
            print(f"  ✗ {label}: 期望 {expected}, 得到 {result}")

    print("\n[2] can_access_customer")

    hq_id = str(ORG_HQ.id)
    branch_a_id = str(ORG_BRANCH_A.id)
    branch_b_id = str(ORG_BRANCH_B.id)

    # SYSTEM_ADMIN 可访问所有
    u = make_user("sys", ROLE_SYSTEM_ADMIN, ORG_HQ)
    check("SYSTEM_ADMIN 访问 HQ 客户", u, hq_id, True)
    check("SYSTEM_ADMIN 访问 BRANCH_A 客户", u, branch_a_id, True)
    check("SYSTEM_ADMIN 访问 None org 客户", u, None, True)

    # HQ_ADMIN (demo) 访问本机构
    u = make_user("hq", ROLE_HQ_ADMIN, ORG_HQ, demo=True)
    check("HQ_ADMIN (demo) 访问同 org 客户", u, hq_id, True)
    check("HQ_ADMIN (demo) 访问其他 org 客户", u, branch_a_id, False)

    # BRANCH_ADMIN (demo) 访问本机构
    u = make_user("branch", ROLE_BRANCH_ADMIN, ORG_BRANCH_A, demo=True)
    check("BRANCH_ADMIN (demo) 访问同 org 客户", u, branch_a_id, True)
    check("BRANCH_ADMIN (demo) 访问其他 org 客户", u, hq_id, False)
    check("BRANCH_ADMIN (demo) 访问 None org 客户", u, None, False)

    # AGENT (demo) 访问同机构
    u = make_user("agent", ROLE_AGENT, ORG_HQ, demo=True)
    check("AGENT (demo) 访问同 org 客户", u, hq_id, True)
    check("AGENT (demo) 访问其他 org 客户", u, branch_b_id, False)

    # AGENT (非demo) 不可访问非自己数据
    u = make_user("agent2", ROLE_AGENT, ORG_HQ, demo=False)
    check("AGENT (非demo) 访问同 org 客户", u, hq_id, False)

    return passed, failed


def test_can_access_document():
    """测试 can_access_document（应与 can_access_customer 一致）。"""
    from app.core.authorization import DataPermissionChecker

    passed = 0
    failed = 0

    print("\n[3] can_access_document")

    hq_id = str(ORG_HQ.id)
    u = make_user("agent", ROLE_AGENT, ORG_HQ, demo=True)
    checker = DataPermissionChecker(u)  # type: ignore[arg-type]

    r1 = checker.can_access_document(hq_id)
    r2 = checker.can_access_customer(hq_id)
    if r1 == r2:
        passed += 1
        print(f"  ✓ can_access_document 与 can_access_customer 结果一致")
    else:
        failed += 1
        print(f"  ✗ can_access_document({r1}) != can_access_customer({r2})")

    return passed, failed


def test_can_manage_user():
    """测试 can_manage_user。"""
    from app.core.authorization import DataPermissionChecker

    passed = 0
    failed = 0

    def check(label: str, manager: MockUser, target: MockUser, expected: bool):
        nonlocal passed, failed
        checker = DataPermissionChecker(manager)  # type: ignore[arg-type]
        result = checker.can_manage_user(target)  # type: ignore[arg-type]
        if result == expected:
            passed += 1
            print(f"  ✓ {label}")
        else:
            failed += 1
            print(f"  ✗ {label}: 期望 {expected}, 得到 {result}")

    print("\n[4] can_manage_user")

    admin = make_user("admin", ROLE_SYSTEM_ADMIN, ORG_HQ)
    hq_admin = make_user("hq", ROLE_HQ_ADMIN, ORG_HQ, demo=True)
    branch_admin = make_user("branch", ROLE_BRANCH_ADMIN, ORG_BRANCH_A, demo=True)
    agent = make_user("agent", ROLE_AGENT, ORG_HQ, demo=True)

    check("SYSTEM_ADMIN 可管理任何人", admin, agent, True)
    check("不能管理自己", admin, admin, False)

    check("HQ_ADMIN (demo) 可管理同 org AGENT", hq_admin, agent, True)
    check("HQ_ADMIN (demo) 不可管理同 role", hq_admin, hq_admin, False)

    check("BRANCH_ADMIN (demo) 不可管理不同 org 用户", branch_admin, agent, False)
    check("AGENT 不可管理任何人", agent, hq_admin, False)

    return passed, failed


def test_demo_user_scenario():
    """测试 Demo 模式下的典型场景。"""
    from app.core.authorization import DataPermissionChecker

    passed = 0
    failed = 0

    print("\n[5] Demo 模式典型场景")

    # Demo 用户都在同一 org 下
    demo_org_id = str(ORG_HQ.id)

    roles_scenarios = [
        ("AGENT",        True,  "Demo AGENT 可见同 org 客户"),
        ("TEAM_LEADER",  True,  "Demo TEAM_LEADER 可见同 org 客户"),
        ("BRANCH_ADMIN", True,  "Demo BRANCH_ADMIN 可见同 org 客户"),
        ("HQ_ADMIN",     True,  "Demo HQ_ADMIN 可见同 org 客户"),
        ("SYSTEM_ADMIN", True,  "Demo SYSTEM_ADMIN 可见所有客户"),
    ]

    for role_code, expected, label in roles_scenarios:
        role = MockRole(
            id=uuid.uuid4(), code=role_code, name=role_code, level=100 if role_code == "SYSTEM_ADMIN" else 1
        )
        u = make_user(role_code, role, ORG_HQ, demo=True)
        checker = DataPermissionChecker(u)  # type: ignore[arg-type]
        result = checker.can_access_customer(demo_org_id)
        if result == expected:
            passed += 1
            print(f"  ✓ {label}")
        else:
            failed += 1
            print(f"  ✗ {label}: 期望 {expected}, 得到 {result}")

    return passed, failed


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main():
    print("=" * 60)
    print("Phase 4-3: IDOR 防护验证")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    tests = [
        test_filter_accessible_org_ids,
        test_can_access_customer,
        test_can_access_document,
        test_can_manage_user,
        test_demo_user_scenario,
    ]

    for test_fn in tests:
        try:
            p, f = test_fn()
            total_passed += p
            total_failed += f
        except Exception as e:
            print(f"  ✗ {test_fn.__name__} 异常: {e}")
            import traceback
            traceback.print_exc()
            total_failed += 1

    print("\n" + "=" * 60)
    print(f"总计: {total_passed} 通过, {total_failed} 失败")
    print("=" * 60)

    if total_failed > 0:
        sys.exit(1)
    else:
        print("\n✅ 所有 IDOR 防护测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()
