import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.base import Base
from app.models.role import Role
from app.models.permission import Permission, role_permissions
from app.models.organization import Organization, OrgType
from app.models.user import User
from app.repositories.user_repo import UserRepository


# ---- 种子数据定义 ----

ROLES = [
    {"code": "admin", "name": "系统管理员", "description": "系统最高权限管理员", "level": 100},
    {"code": "manager", "name": "团队管理者", "description": "分公司/团队管理者", "level": 50},
    {"code": "sales", "name": "销售专员", "description": "一线销售保险业务人员", "level": 10},
]

PERMISSIONS = [
    {"code": "customer:read", "name": "查看客户", "module": "customer"},
    {"code": "customer:write", "name": "编辑客户", "module": "customer"},
    {"code": "customer:delete", "name": "删除客户", "module": "customer"},
    {"code": "product:read", "name": "查看产品", "module": "product"},
    {"code": "product:write", "name": "编辑产品", "module": "product"},
    {"code": "ai:chat", "name": "AI 对话", "module": "ai"},
    {"code": "report:read", "name": "查看报表", "module": "report"},
    {"code": "user:manage", "name": "用户管理", "module": "system"},
    {"code": "role:manage", "name": "角色管理", "module": "system"},
]

ORGANIZATIONS = [
    {"name": "华安保险总部", "type": OrgType.HQ, "parent_id": None},
    {"name": "上海分公司", "type": OrgType.BRANCH, "parent_id": None},
    {"name": "北京分公司", "type": OrgType.BRANCH, "parent_id": None},
]

DEMO_USERS = [
    {
        "phone": "13800138000",
        "name": "演示用户",
        "password": "888888",
        "role_code": "sales",
        "org_name": "华安保险总部",
    },
]


async def seed_database():
    """填充种子数据到数据库。"""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        now = datetime.now(timezone.utc)

        # ---- Roles ----
        print("📦 创建角色...")
        role_map: dict[str, uuid.UUID] = {}
        for r in ROLES:
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
        await session.flush()

        # ---- Permissions ----
        print("📦 创建权限...")
        perm_map: dict[str, uuid.UUID] = {}
        for p in PERMISSIONS:
            perm = Permission(
                id=uuid.uuid4(),
                code=p["code"],
                name=p["name"],
                module=p["module"],
                created_at=now,
                updated_at=now,
            )
            session.add(perm)
            perm_map[p["code"]] = perm.id
        await session.flush()

        # ---- Role-Permission bindings ----
        print("📦 绑定角色权限...")
        # admin 获得所有权限
        for perm_id in perm_map.values():
            session.execute(
                role_permissions.insert().values(
                    role_id=role_map["admin"],
                    permission_id=perm_id,
                )
            )
        # sales 获得部分权限
        sales_perms = ["customer:read", "customer:write", "product:read", "ai:chat", "report:read"]
        for code in sales_perms:
            if code in perm_map:
                session.execute(
                    role_permissions.insert().values(
                        role_id=role_map["sales"],
                        permission_id=perm_map[code],
                    )
                )
        # manager 获得 sales 权限 + 用户管理
        manager_perms = sales_perms + ["user:manage", "customer:delete"]
        for code in manager_perms:
            if code in perm_map:
                session.execute(
                    role_permissions.insert().values(
                        role_id=role_map["manager"],
                        permission_id=perm_map[code],
                    )
                )
        await session.flush()

        # ---- Organizations ----
        print("📦 创建组织...")
        org_map: dict[str, uuid.UUID] = {}
        for org_data in ORGANIZATIONS:
            org = Organization(
                id=uuid.uuid4(),
                name=org_data["name"],
                type=org_data["type"],
                parent_id=org_data["parent_id"],
                created_at=now,
                updated_at=now,
            )
            session.add(org)
            org_map[org_data["name"]] = org.id
        await session.flush()

        # ---- Demo Users ----
        print("📦 创建演示用户...")
        for u in DEMO_USERS:
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
        await session.flush()

        await session.commit()
        print("✅ 种子数据填充完成！")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
