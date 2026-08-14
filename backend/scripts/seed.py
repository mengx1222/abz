"""种子数据脚本 — 初始化角色、权限、组织、演示用户。

运行方式:
    cd backend && python -m scripts.seed

依赖: DATABASE_URL 指向一个已经运行 alembic upgrade head 的 PostgreSQL 实例。
"""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.base import Base
from app.models.role import Role
from app.models.permission import Permission, role_permissions
from app.models.organization import Organization, OrgType
from app.models.user import User
from app.services.training_service import seed_training_scenarios


# ============================================================
#  7 标准角色 (decisions.md §6 — authoritative)
# ============================================================
ROLES = [
    {"code": "SYSTEM_ADMIN",  "name": "系统管理员",   "description": "平台最高权限，管理所有系统配置", "level": 100},
    {"code": "HQ_ADMIN",      "name": "总部管理员",   "description": "总部运营管理，查看全局数据",    "level": 90},
    {"code": "BRANCH_ADMIN",  "name": "分公司管理员", "description": "分公司运营管理，管理下属团队",  "level": 80},
    {"code": "TEAM_LEADER",   "name": "团队长",       "description": "团队日常管理，查看团队数据",    "level": 60},
    {"code": "COMPLIANCE",     "name": "合规专员",     "description": "内容合规审核，查看合规报告",    "level": 70},
    {"code": "KNOWLEDGE_ADMIN","name": "知识库管理员", "description": "管理知识库内容，审核文档",      "level": 50},
    {"code": "AGENT",         "name": "代理人",       "description": "一线保险销售代理人",           "level": 10},
]

# ============================================================
#  权限定义
# ============================================================
PERMISSIONS = [
    # 客户模块
    {"code": "customer:read",   "name": "查看客户",     "module": "customer"},
    {"code": "customer:write",  "name": "编辑客户",     "module": "customer"},
    {"code": "customer:delete",  "name": "删除客户",     "module": "customer"},
    {"code": "customer:export",  "name": "导出客户",     "module": "customer"},
    # AI 模块
    {"code": "ai:chat",         "name": "AI 对话",      "module": "ai"},
    {"code": "ai:script",       "name": "AI 话术生成",   "module": "ai"},
    {"code": "ai:training",     "name": "AI 陪练",      "module": "ai"},
    # 知识库模块
    {"code": "knowledge:read",  "name": "查看知识库",   "module": "knowledge"},
    {"code": "knowledge:write", "name": "编辑知识库",   "module": "knowledge"},
    {"code": "knowledge:audit", "name": "审核知识库",   "module": "knowledge"},
    # 社区模块
    {"code": "community:read",  "name": "查看社区",     "module": "community"},
    {"code": "community:write", "name": "发帖/评论",    "module": "community"},
    {"code": "community:moderate","name": "社区管理",    "module": "community"},
    # 报表模块
    {"code": "report:read",     "name": "查看报表",     "module": "report"},
    {"code": "report:export",   "name": "导出报表",     "module": "report"},
    # 系统模块
    {"code": "user:manage",     "name": "用户管理",     "module": "system"},
    {"code": "role:manage",     "name": "角色管理",     "module": "system"},
    {"code": "org:manage",      "name": "组织管理",     "module": "system"},
    {"code": "system:config",   "name": "系统配置",     "module": "system"},
    {"code": "compliance:review","name": "合规审查",     "module": "compliance"},
    {"code": "compliance:report","name": "合规报表",     "module": "compliance"},
]

# ============================================================
#  角色-权限映射
# ============================================================
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "SYSTEM_ADMIN": [
        "customer:read", "customer:write", "customer:delete", "customer:export",
        "ai:chat", "ai:script", "ai:training",
        "knowledge:read", "knowledge:write", "knowledge:audit",
        "community:read", "community:write", "community:moderate",
        "report:read", "report:export",
        "user:manage", "role:manage", "org:manage", "system:config",
        "compliance:review", "compliance:report",
    ],
    "HQ_ADMIN": [
        "customer:read", "customer:write", "customer:export",
        "ai:chat", "ai:script", "ai:training",
        "knowledge:read", "knowledge:audit",
        "community:read", "community:moderate",
        "report:read", "report:export",
        "user:manage", "org:manage",
        "compliance:review", "compliance:report",
    ],
    "BRANCH_ADMIN": [
        "customer:read", "customer:write", "customer:export",
        "ai:chat", "ai:script", "ai:training",
        "knowledge:read",
        "community:read", "community:moderate",
        "report:read",
        "user:manage",
        "compliance:review",
    ],
    "TEAM_LEADER": [
        "customer:read", "customer:write", "customer:export",
        "ai:chat", "ai:script", "ai:training",
        "knowledge:read",
        "community:read", "community:write",
        "report:read",
    ],
    "COMPLIANCE": [
        "customer:read",
        "ai:chat",
        "knowledge:read", "knowledge:audit",
        "community:read", "community:moderate",
        "report:read",
        "compliance:review", "compliance:report",
    ],
    "KNOWLEDGE_ADMIN": [
        "customer:read",
        "ai:chat",
        "knowledge:read", "knowledge:write", "knowledge:audit",
        "community:read",
        "report:read",
    ],
    "AGENT": [
        "customer:read", "customer:write",
        "ai:chat", "ai:script", "ai:training",
        "knowledge:read",
        "community:read", "community:write",
        "report:read",
    ],
}

# ============================================================
#  组织结构
# ============================================================
ORGANIZATIONS = [
    {"name": "华安保险总部",           "type": OrgType.HQ,     "parent_name": None},
    {"name": "上海分公司",             "type": OrgType.BRANCH, "parent_name": "华安保险总部"},
    {"name": "北京分公司",             "type": OrgType.BRANCH, "parent_name": "华安保险总部"},
    {"name": "上海分公司-浦东团队",    "type": OrgType.TEAM,   "parent_name": "上海分公司"},
    {"name": "上海分公司-徐汇团队",    "type": OrgType.TEAM,   "parent_name": "上海分公司"},
    {"name": "北京分公司-朝阳团队",    "type": OrgType.TEAM,   "parent_name": "北京分公司"},
]

# ============================================================
#  演示用户
# ============================================================
DEMO_USERS = [
    {
        "phone": "13800138000",
        "name": "林思远",
        "password": "888888",
        "role_code": "AGENT",
        "org_name": "上海分公司-浦东团队",
    },
    {
        "phone": "13800138001",
        "name": "张伟",
        "password": "888888",
        "role_code": "TEAM_LEADER",
        "org_name": "上海分公司-浦东团队",
    },
    {
        "phone": "13800138002",
        "name": "李芳",
        "password": "888888",
        "role_code": "BRANCH_ADMIN",
        "org_name": "上海分公司",
    },
    {
        "phone": "13800138003",
        "name": "王强",
        "password": "888888",
        "role_code": "SYSTEM_ADMIN",
        "org_name": "华安保险总部",
    },
]


async def seed_database():
    """填充种子数据到数据库。如果数据已存在则跳过。"""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        now = datetime.now(timezone.utc)

        # ---- 1. Roles (幂等: 跳过已存在的) ----
        print("📦 创建角色...")
        role_map: dict[str, uuid.UUID] = {}
        for r in ROLES:
            existing = await session.execute(select(Role).where(Role.code == r["code"]))
            existing_role = existing.scalar_one_or_none()
            if existing_role:
                role_map[r["code"]] = existing_role.id
                print(f"   ⏭️  角色 {r['code']} 已存在，跳过")
                continue
            role = Role(
                id=uuid.uuid4(),
                code=r["code"],
                name=r["name"],
                description=r["description"],
                level=r["level"],
                created_at=now,
                updated_at=now,
            )
            session.add(role)
            role_map[r["code"]] = role.id
            print(f"   ✅ 角色 {r['code']} ({r['name']})")
        await session.flush()

        # ---- 2. Permissions (幂等) ----
        print("\n📦 创建权限...")
        perm_map: dict[str, uuid.UUID] = {}
        for p in PERMISSIONS:
            existing = await session.execute(select(Permission).where(Permission.code == p["code"]))
            existing_perm = existing.scalar_one_or_none()
            if existing_perm:
                perm_map[p["code"]] = existing_perm.id
                continue
            perm = Permission(
                id=uuid.uuid4(),
                code=p["code"],
                name=p["name"],
                module=p.get("module"),
                created_at=now,
                updated_at=now,
            )
            session.add(perm)
            perm_map[p["code"]] = perm.id
        await session.flush()

        # ---- 3. Role-Permission bindings ----
        print("\n📦 绑定角色权限...")
        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            role_id = role_map[role_code]
            for perm_code in perm_codes:
                if perm_code not in perm_map:
                    continue
                # 检查是否已绑定
                existing = await session.execute(
                    select(role_permissions).where(
                        role_permissions.c.role_id == role_id,
                        role_permissions.c.permission_id == perm_map[perm_code],
                    )
                )
                if existing.first():
                    continue
                session.execute(
                    role_permissions.insert().values(
                        role_id=role_id,
                        permission_id=perm_map[perm_code],
                    )
                )
            print(f"   ✅ {role_code}: {len(perm_codes)} 权限")
        await session.flush()

        # ---- 4. Organizations (层级创建) ----
        print("\n📦 创建组织...")
        org_map: dict[str, uuid.UUID] = {}
        for org_data in ORGANIZATIONS:
            existing = await session.execute(
                select(Organization).where(Organization.name == org_data["name"])
            )
            existing_org = existing.scalar_one_or_none()
            if existing_org:
                org_map[org_data["name"]] = existing_org.id
                continue
            parent_id = None
            if org_data["parent_name"] and org_data["parent_name"] in org_map:
                parent_id = org_map[org_data["parent_name"]]
            org = Organization(
                id=uuid.uuid4(),
                name=org_data["name"],
                type=org_data["type"],
                parent_id=parent_id,
                created_at=now,
                updated_at=now,
            )
            session.add(org)
            org_map[org_data["name"]] = org.id
            print(f"   ✅ {org_data['name']} ({org_data['type'].value})")
        await session.flush()

        # ---- 5. Demo Users (幂等) ----
        print("\n📦 创建演示用户...")
        for u in DEMO_USERS:
            existing = await session.execute(select(User).where(User.phone == u["phone"]))
            existing_user = existing.scalar_one_or_none()
            if existing_user:
                print(f"   ⏭️  用户 {u['phone']} ({u['name']}) 已存在，跳过")
                continue
            user = User(
                id=uuid.uuid4(),
                phone=u["phone"],
                name=u["name"],
                password_hash=hash_password(u["password"]),
                role_id=role_map[u["role_code"]],
                organization_id=org_map[u["org_name"]],
                status="active",
                demo_mode=True,
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            print(f"   ✅ {u['name']} ({u['phone']}) → {u['role_code']} @ {u['org_name']}")
        await session.flush()

        # ---- 6. Training Scenarios (幂等) ----
        print("\n📦 创建训练场景...")
        training_created = await seed_training_scenarios(session)
        if training_created:
            print(f"   ✅ 新增训练场景: {training_created} 个")
        else:
            print("   ⏭️  训练场景已存在，跳过")
        await session.flush()

        await session.commit()
        print(f"\n🎉 种子数据填充完成！")
        print(f"   角色: {len(ROLES)} 个")
        print(f"   权限: {len(PERMISSIONS)} 个")
        print(f"   组织: {len(ORGANIZATIONS)} 个")
        print(f"   用户: {len(DEMO_USERS)} 个 (全部为演示模式)")
        print(f"   训练场景: {training_created} 个 (本次新增)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
