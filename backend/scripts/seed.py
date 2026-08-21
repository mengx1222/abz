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
from app.models.customer import Customer, CustomerFollowup, CustomerInteraction
from app.services.training_service import seed_training_scenarios
from scripts.e2e_seed_knowledge import seed_e2e_knowledge


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
#  演示用户（RDY 阶段2：密码从 settings.DEMO_PASSWORD 注入，不硬编码）
#  - E2E Test Credential（CI-only）：默认 888888（frontend/e2e/global-setup.ts 使用，
#    仅用于 GitHub Actions 云端测试，代码内标注 CI-only）
#  - Demo Credential（开发/演示环境）：默认 888888，可 AZB_DEMO_PASSWORD 覆盖
#  - Pilot Credential（正式 Internal Pilot）：13800138000 + 部署时注入的强密码
#    （AZB_DEMO_PASSWORD = GitHub Secret / 外部 secret store / workflow env），
#    禁止沿用默认值作为正式试点登录凭据
#  - Production Secret：AI_API_KEY / DATABASE_URL / JWT_SECRET_KEY 等走 Secrets store
# ============================================================
DEMO_USERS = [
    {
        "phone": "13800138000",
        "name": "林思远",
        "role_code": "AGENT",
        "org_name": "上海分公司-浦东团队",
    },
    {
        "phone": "13800138001",
        "name": "张伟",
        "role_code": "TEAM_LEADER",
        "org_name": "上海分公司-浦东团队",
    },
    {
        "phone": "13800138002",
        "name": "李芳",
        "role_code": "BRANCH_ADMIN",
        "org_name": "上海分公司",
    },
    {
        "phone": "13800138003",
        "name": "王强",
        "role_code": "SYSTEM_ADMIN",
        "org_name": "华安保险总部",
    },
]

# ============================================================
#  Pilot 演示客户（ULTIMATE Pilot Prep + RDY 阶段1 强化）
#  生产模式（DEMO_MODE=false）下 AGENT 仅可见 assigned_to=本人 的客户（P0-1 语义），
#  因此演示客户必须挂到 AGENT 演示用户（13800138000 林思远）名下，试点演示才有数据。
#
#  数据标识（稳定 identifier/tags，不加 schema）：
#   - tags 含 "PILOT"：Internal Pilot 合成演示数据（可重复、脱敏，无真实客户信息）
#   - tags 含 "COMPLIANCE_RISK"：合规高风险案例（返佣/承诺收益诉求）→ Compliance RED 演练
#   - tags 含 "OBJECTION"：常见异议场景（价格/理赔时效/线上投保疑虑）→ 异议处理演练
#   phone 唯一用于幂等；全部 assigned_to=13800138000（AGENT 林思远），organization 一致。
# ============================================================
PILOT_CUSTOMERS = [
    {
        "name": "陈女士", "age": 42, "gender": "female", "phone": "13900000001",
        "customer_type": "active", "current_stage": "needs_analysis",
        "intention_level": 3, "insurance_type": "医疗险", "source_channel": "转介绍",
        "notes": "关注百万医疗险，为家人咨询", "tags": ["PILOT"],
    },
    {
        "name": "刘先生", "age": 35, "gender": "male", "phone": "13900000002",
        "customer_type": "active", "current_stage": "proposal",
        "intention_level": 4, "insurance_type": "重疾险", "source_channel": "门店",
        "notes": "预算约 8000 元/年，方案待定", "tags": ["PILOT"],
    },
    {
        "name": "周女士", "age": 50, "gender": "female", "phone": "13900000003",
        "customer_type": "follow_up", "current_stage": "initial_contact",
        "intention_level": 2, "insurance_type": "医疗险", "source_channel": "电话",
        "notes": "初次咨询，需回访", "tags": ["PILOT"],
    },
    {
        "name": "赵先生", "age": 45, "gender": "male", "phone": "13900000004",
        "customer_type": "active", "current_stage": "proposal",
        "intention_level": 5, "insurance_type": "医疗险", "source_channel": "朋友介绍",
        "notes": "方案阶段提出返佣与承诺保本收益要求（合规高风险案例，须按红线拒绝并上报）",
        "tags": ["PILOT", "COMPLIANCE_RISK"],
    },
    {
        "name": "孙女士", "age": 38, "gender": "female", "phone": "13900000005",
        "customer_type": "active", "current_stage": "needs_analysis",
        "intention_level": 3, "insurance_type": "重疾险", "source_channel": "线上活动",
        "notes": "对线上投保安全性、理赔时效有疑虑（常见异议场景，需提供证据打消顾虑）",
        "tags": ["PILOT", "OBJECTION"],
    },
]


# 模板占位密码（.env.production 未修改时）：seed 必须 fail-fast，不得 fallback 默认值
_PLACEHOLDER_PASSWORDS = ("CHANGE_ME_PILOT_STRONG_PASSWORD",)


def validate_pilot_password() -> None:
    """PCRED 阶段3：正式 Pilot/生产 seed 前校验 AZB_DEMO_PASSWORD 不是模板占位。

    - 默认值 888888：仅 CI/Demo 环境测试凭据（E2E/CI-only），不在此处阻断；
    - .env.production 模板占位值（CHANGE_ME_*）：真实 Pilot/生产复制模板未改密码时
      fail-fast 报错，明确 BLOCKED —— 绝不静默使用默认/占位密码创建 Pilot 用户。
    """
    if settings.DEMO_PASSWORD in _PLACEHOLDER_PASSWORDS:
        raise RuntimeError(
            "AZB_DEMO_PASSWORD 仍为模板占位值（CHANGE_ME_PILOT_STRONG_PASSWORD）。"
            "正式 Internal Pilot / 生产执行 seed 前必须通过 Secret/env 注入强密码"
            "（生成: python -c 'import secrets;print(secrets.token_urlsafe(24))'）。"
            "当前状态: BLOCKED — HUMAN SECRET ROTATION REQUIRED"
        )


async def seed_pilot_customers(session: AsyncSession, agent_phone: str = "13800138000") -> int:
    """幂等创建试点演示客户（含互动 + 跟进），返回本次新增数。

    生产 AGENT 仅可访问本人 assigned 客户，故全部挂到 AGENT 演示用户名下。
    """
    agent = (
        await session.execute(select(User).where(User.phone == agent_phone))
    ).scalar_one_or_none()
    if agent is None:
        print(f"   ⏭️  AGENT 演示用户 {agent_phone} 不存在，跳过试点客户 seed")
        return 0

    created = 0
    now = datetime.now(timezone.utc)
    for c in PILOT_CUSTOMERS:
        existing = await session.execute(select(Customer).where(Customer.phone == c["phone"]))
        if existing.scalar_one_or_none():
            continue
        customer = Customer(
            name=c["name"],
            age=c["age"],
            gender=c["gender"],
            phone=c["phone"],
            customer_type=c["customer_type"],
            current_stage=c["current_stage"],
            intention_level=c["intention_level"],
            insurance_type=c["insurance_type"],
            source_channel=c["source_channel"],
            notes=c["notes"],
            tags=c.get("tags") or ["PILOT"],
            assigned_to=agent.id,
            organization_id=agent.organization_id,
            created_at=now,
            updated_at=now,
        )
        session.add(customer)
        await session.flush()
        session.add(CustomerInteraction(
            customer_id=customer.id,
            type="phone",
            direction="inbound",
            content="初次电话沟通，介绍产品保障范围。",
            outcome="客户有兴趣，约定跟进",
            created_at=now,
            updated_at=now,
        ))
        session.add(CustomerFollowup(
            customer_id=customer.id,
            scheduled_date=now,
            status="pending",
            content="跟进客户意向，发送产品资料",
            created_at=now,
            updated_at=now,
        ))
        created += 1
        print(f"   ✅ 试点客户 {c['name']} ({c['phone']}) → {agent.name}")
    if created:
        await session.flush()
    return created


async def seed_database():
    """填充种子数据到数据库。如果数据已存在则跳过。"""
    # PCRED 阶段3：正式 Pilot/生产环境密码占位时 fail-fast（不静默 fallback）
    validate_pilot_password()
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
                # Task 35：缺少 await 导致协程从未执行 —— 角色-权限绑定静默不落库
                # （seed 输出的"✅ xxx: N 权限"仅为打印，实际绑定从未插入）。
                # 修复后绑定真正写入，seed 幂等性回归测试（test_seed_idempotency.py）覆盖。
                await session.execute(
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
                # RDY 阶段2：密码统一从 settings.DEMO_PASSWORD 注入（默认 888888 仅 CI/Demo；
                # 正式 Pilot/生产由 AZB_DEMO_PASSWORD env 提供强密码）
                password_hash=hash_password(settings.DEMO_PASSWORD),
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

        # ---- 7. Pilot 演示客户（ULTIMATE Pilot Prep，幂等）----
        print("\n📦 创建试点演示客户...")
        customers_created = await seed_pilot_customers(session)
        print(f"   试点客户: {customers_created} 个 (本次新增)")

        # ---- 8. 产品知识库/文档（幂等，复用 e2e_seed_knowledge）----
        print("\n📦 创建产品知识库...")
        try:
            kb_created = await seed_e2e_knowledge(session)
            print(f"   知识库: {'本次新建' if kb_created else '已存在，跳过'}")
        except Exception as e:
            # 知识库 seed 失败（如 AI/embedding 不可用）不阻塞整体 seed，明确告警
            print(f"   ⚠️  知识库 seed 失败（可稍后单独运行 scripts/e2e_seed_knowledge.py）: {e}")
        await session.flush()

        await session.commit()
        print(f"\n🎉 种子数据填充完成！")
        print(f"   角色: {len(ROLES)} 个")
        print(f"   权限: {len(PERMISSIONS)} 个")
        print(f"   组织: {len(ORGANIZATIONS)} 个")
        print(f"   用户: {len(DEMO_USERS)} 个 (全部为演示模式)")
        print(f"   训练场景: {training_created} 个 (本次新增)")
        print(f"   试点客户: {customers_created} 个 (本次新增)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
