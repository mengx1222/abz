"""Phase 3 实施脚本 — SQLite 本地数据库 + 完整 Seed

执行流程:
  1. 配置 SQLite 数据库 (aiosqlite)
  2. 用 Base.metadata.create_all() 创建所有 31 张表
  3. 执行增强版 Seed（填充所有业务模块演示数据）
  4. 输出验证报告

运行方式:
    cd /home/z/my-project/backend && .venv/bin/python -m scripts.phase3_setup
"""
import asyncio
import os
import sys
import uuid
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 强制使用 SQLite
os.environ["AZB_DATABASE_URL"] = "sqlite+aiosqlite:///./data/abz_dev.db"
os.environ["AZB_DEMO_MODE"] = "false"
os.environ["AZB_AI_PROVIDER"] = "mock"
os.environ["AZB_DEBUG"] = "false"
os.environ["AZB_APP_ENV"] = "development"

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 注册 SQLite 兼容类型处理器
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
if not hasattr(SQLiteTypeCompiler, 'visit_JSONB'):
    SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON
if not hasattr(SQLiteTypeCompiler, 'visit_UUID'):
    SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "TEXT"

from app.core.config import settings
from app.core.security import hash_password
from app.models.base import Base

# 替换 PG 特有类型
import sqlalchemy as sa
for table in Base.metadata.tables.values():
    for col in table.columns:
        tn = col.type.__class__.__name__
        if tn == "Vector":
            col.type = sa.LargeBinary()
        elif tn == "JSONB":
            col.type = sa.JSON()

# 导入所有模型
from app.models import (  # noqa: E402
    Role, Permission, Organization, User,
    Conversation, Message,
    KnowledgeBase, Document, DocumentChunk,
    AIRequestLog, AIFeedback,
    TrainingScenario, TrainingSession, TrainingMessage, TrainingScore,
    Customer, CustomerTag, CustomerInteraction, CustomerFollowup,
    Script, ScriptFavorite, ScriptVersion,
    Post, PostComment, PostLike, PostFavorite,
    Notification, NotificationPreference,
    UserAchievement, AuditLog,
)
from app.models.organization import OrgType

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "abz_dev.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


async def create_all_tables(engine):
    print("=" * 60)
    print("Step 1: Creating database tables (SQLite)")
    print("=" * 60)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ))
        tables = [row[0] for row in result.fetchall()]
        print(f"\n  Created {len(tables)} tables:")
        for t in tables:
            print(f"    - {t}")
    return tables


async def seed_all_data(session_factory):
    print("\n" + "=" * 60)
    print("Step 2: Seeding data")
    print("=" * 60)

    async with session_factory() as session:
        now = datetime.now(timezone.utc)

        # == 1. Roles ==
        roles_data = [
            ("SYSTEM_ADMIN", "系统管理员", "平台最高权限", 100),
            ("HQ_ADMIN", "总部管理员", "总部运营管理", 90),
            ("BRANCH_ADMIN", "分公司管理员", "分公司运营管理", 80),
            ("TEAM_LEADER", "团队长", "团队日常管理", 60),
            ("COMPLIANCE", "合规专员", "内容合规审核", 70),
            ("KNOWLEDGE_ADMIN", "知识库管理员", "管理知识库内容", 50),
            ("AGENT", "代理人", "一线保险销售", 10),
        ]
        print("\n[Roles]")
        role_map = {}
        for code, name, desc, level in roles_data:
            r = Role(code=code, name=name, description=desc, level=level, created_at=now, updated_at=now)
            session.add(r)
            role_map[code] = r
        await session.flush()
        for r in role_map.values():
            print(f"  + {r.code} ({r.name}) id={r.id}")

        # == 2. Organizations ==
        orgs_data = [
            ("华安保险总部", OrgType.HQ, None),
            ("上海分公司", OrgType.BRANCH, "华安保险总部"),
            ("北京分公司", OrgType.BRANCH, "华安保险总部"),
            ("上海分公司-浦东团队", OrgType.TEAM, "上海分公司"),
            ("上海分公司-徐汇团队", OrgType.TEAM, "上海分公司"),
            ("北京分公司-朝阳团队", OrgType.TEAM, "北京分公司"),
        ]
        print("\n[Organizations]")
        org_map = {}
        for name, otype, parent_name in orgs_data:
            parent_id = org_map[parent_name].id if parent_name and parent_name in org_map else None
            o = Organization(name=name, type=otype, parent_id=parent_id, created_at=now, updated_at=now)
            session.add(o)
            org_map[name] = o
        await session.flush()
        for o in org_map.values():
            print(f"  + {o.name} ({o.type.value}) id={o.id}")

        # == 3. Users ==
        users_data = [
            ("13800138000", "林思远", "AGENT", "上海分公司-浦东团队"),
            ("13800138001", "张伟", "TEAM_LEADER", "上海分公司-浦东团队"),
            ("13800138002", "李芳", "BRANCH_ADMIN", "上海分公司"),
            ("13800138003", "王强", "SYSTEM_ADMIN", "华安保险总部"),
        ]
        print("\n[Users]")
        user_map = {}
        for phone, name, role_code, org_name in users_data:
            u = User(
                phone=phone, name=name,
                password_hash=hash_password("888888"),
                role_id=role_map[role_code].id,
                organization_id=org_map[org_name].id,
                status="active", demo_mode=True,
                created_at=now, updated_at=now,
            )
            session.add(u)
            user_map[phone] = u
        await session.flush()
        for u in user_map.values():
            print(f"  + {u.name} ({u.phone}) -> {u.role_id}")

        linsy = user_map["13800138000"]

        # == 4. Customer Tags ==
        tags = ["高价值", "活跃客户", "潜在客户", "已购医疗险", "已购重疾险",
                "车险客户", "家庭保障", "企业客户", "转介绍", "VIP"]
        print("\n[CustomerTags]")
        for t in tags:
            session.add(CustomerTag(name=t, category="general", created_at=now, updated_at=now))
        await session.flush()
        print(f"  + {len(tags)} tags")

        # == 5. Customers (20) ==
        print("\n[Customers]")
        customer_names = [
            "张明华", "李秀英", "王建国", "刘芳芳", "陈志强",
            "杨丽萍", "赵国安", "黄小红", "周大伟", "吴美玲",
            "郑小龙", "孙雅婷", "马文博", "朱丽华", "胡建华",
            "林小燕", "何志明", "罗晓峰", "谢玉兰", "唐永强",
        ]
        ctypes = ["prospective", "active", "active", "lapsed", "prospective",
                  "active", "prospective", "active", "prospective", "active",
                  "lapsed", "prospective", "active", "active", "prospective",
                  "active", "prospective", "active", "lapsed", "active"]
        itypes = ["医疗险", "重疾险", "年金险", "意外险", "医疗险",
                  "寿险", "车险", "医疗险", "重疾险", "年金险",
                  "意外险", "医疗险", "寿险", "医疗险", "重疾险",
                  "年金险", "意外险", "医疗险", "车险", "寿险"]
        stages = ["initial_contact", "needs_analysis", "proposal", "presentation", "negotiation",
                 "closed_won", "initial_contact", "needs_analysis", "proposal", "closed_won",
                 "closed_lost", "initial_contact", "needs_analysis", "presentation", "negotiation",
                 "closed_won", "initial_contact", "needs_analysis", "closed_lost", "closed_won"]
        channels = ["referral", "cold_call", "online", "walk_in", "referral",
                   "online", "cold_call", "referral", "walk_in", "online",
                   "referral", "cold_call", "online", "walk_in", "referral",
                   "cold_call", "online", "referral", "walk_in", "online"]

        customer_ids = []
        for i, name in enumerate(customer_names):
            c = Customer(
                name=name, age=25 + (i % 40),
                gender="male" if i % 3 != 0 else "female",
                phone=f"139{str(i+10000000).zfill(8)}",
                customer_type=ctypes[i], tags=json.dumps(["tag1", "tag2"]),
                insurance_type=itypes[i], current_stage=stages[i],
                intention_level=min(5, 1 + i % 5),
                source_channel=channels[i],
                notes=f"{name}的备注信息",
                assigned_to=linsy.id,
                organization_id=org_map["上海分公司-浦东团队"].id,
                created_at=now, updated_at=now,
            )
            session.add(c)
            customer_ids.append(c)
        await session.flush()
        print(f"  + {len(customer_names)} customers")

        # == 6. Scripts (8) ==
        print("\n[Scripts]")
        scripts_data = [
            ("重疾险产品介绍—亲和型", "affinity", "重疾险", "green",
             "您好！很高兴能为您介绍我们的重疾险产品。很多人对重疾险有一些误解，其实它不仅是在您生病时给一笔钱，更是在您康复期间的收入保障。"),
            ("医疗险异议处理—专业型", "professional", "医疗险", "green",
             "关于您提到的医疗险保费问题，我们需要从几个维度来分析。首先，医疗险采用的是自然费率设计..."),
            ("年金险销售—数据驱动型", "data_driven", "年金险", "green",
             "根据最新行业数据统计，65岁以上人群中，有78%的人需要长期护理服务。年金险的IRR可达3.5%以上..."),
            ("意外险促单—简洁型", "concise", "意外险", "yellow",
             "意外险是所有保险中杠杆最高的产品。每天只需2元，即可获得100万意外保障。"),
            ("寿险需求分析—亲和型", "affinity", "寿险", "green",
             "我理解您的顾虑。其实寿险不是为了自己，而是为了爱的人。"),
            ("车险续保话术—专业型", "professional", "车险", "green",
             "您好，您的车险还有30天到期。今年的保费方案有一些变化..."),
            ("全家保障方案—数据驱动型", "data_driven", "综合", "yellow",
             "根据中国家庭保障缺口调查报告，78%的家庭保险配置不足。"),
            ("重疾险对比分析—简洁型", "concise", "重疾险", "green",
             "我们的重疾险覆盖120种重大疾病+60种轻症。相比同类产品，保费低15%但保额高20%。"),
        ]
        for title, style, product, comp, content in scripts_data:
            session.add(Script(
                title=title, style=style, content=content,
                product_type=product, compliance_status=comp,
                customer_context=json.dumps({"age": "30-40"}),
                compliance_issues=json.dumps([]),
                created_by=linsy.id, created_at=now, updated_at=now,
            ))
        await session.flush()
        print(f"  + {len(scripts_data)} scripts")

        # == 7. Training Scenarios (6) ==
        print("\n[TrainingScenarios]")
        scenarios_data = [
            ("首次接触陌生客户", "入门", "医疗险", "initial_contact"),
            ("重疾险需求挖掘", "进阶", "重疾险", "needs_analysis"),
            ("年金险异议处理", "挑战", "年金险", "negotiation"),
            ("家庭保障方案推荐", "进阶", "综合", "proposal"),
            ("车险续保催促", "入门", "车险", "closing"),
            ("寿险理念沟通", "挑战", "寿险", "initial_contact"),
        ]
        for title, diff, prod, stage in scenarios_data:
            session.add(TrainingScenario(
                title=title, description=f"陪练场景：{title}",
                difficulty=diff, product_focus=prod, sales_stage=stage,
                customer_persona=json.dumps({"name": "李先生", "age": 35}),
                evaluation_criteria=json.dumps({"product_accuracy": 0.8}),
                duration_minutes=10, is_active=True,
                created_at=now, updated_at=now,
            ))
        await session.flush()
        print(f"  + {len(scenarios_data)} scenarios")

        # == 8. Community Posts (8) ==
        print("\n[CommunityPosts]")
        posts_data = [
            ("实战经验：如何用提问法打开客户话匣子", "experience", "上周我尝试用SPIN提问法...", ["销售技巧", "实战分享"]),
            ("理赔案例：重大疾病险快速理赔全过程", "experience", "最近协助一位客户完成重疾险理赔...", ["理赔案例", "重疾险"]),
            ("新人求助：第一次拜访客户应该准备什么？", "question", "下周要去拜访一位转介绍客户...", ["新人求助"]),
            ("优秀话术模板：医疗险三分钟电梯演讲", "script", "整理了一个有效的医疗险电梯话术...", ["话术模板"]),
            ("知识分享：2024年重疾险新规解读", "knowledge", "2024年重疾险新规发生了哪些变化...", ["重疾险", "法规"]),
            ("销售心得：从被拒绝到成交的5个关键转折", "experience", "今天想分享我最近一单的经历...", ["销售心得"]),
            ("讨论：AI时代保险代理人如何保持竞争力", "discussion", "随着AI工具越来越普及...", ["AI", "行业趋势"]),
            ("经验分享：如何做好老客户的二次开发", "experience", "老客户是金矿！分享3个方法...", ["老客户"]),
        ]
        for title, cat, content, tags in posts_data:
            session.add(Post(
                title=title, content=content, category=cat,
                tags=json.dumps(tags), author_id=linsy.id,
                views_count=10 + len(content) % 200,
                likes_count=5 + len(content) % 50,
                comments_count=len(content) % 10,
                created_at=now - timedelta(days=len(content) % 30),
                updated_at=now, created_by=linsy.id,
            ))
        await session.flush()
        print(f"  + {len(posts_data)} posts")

        # == 9. Notifications (12) ==
        print("\n[Notifications]")
        notifs = [
            ("followup", "跟进提醒", "您有3位客户需要今日跟进"),
            ("system", "系统更新", "系统已升级到v0.2.0"),
            ("training", "训练提醒", "您本周陪练训练不足2小时"),
            ("team", "团队通知", "张伟发布了新的销售经验分享"),
            ("followup", "客户生日", "客户张明华的生日即将到来"),
            ("system", "合规提醒", "您的3条话术需要更新合规标签"),
            ("community", "社区互动", "您的帖子获得了10个赞"),
            ("training", "成绩更新", "陪练成绩排名上升至第5名"),
            ("followup", "保单续期", "刘芳芳的保单将在30天后到期"),
            ("team", "团队活动", "本月团队销售会议定于周五14:00"),
            ("system", "安全提醒", "建议您更新登录密码"),
            ("community", "评论回复", "李芳回复了您的帖子"),
        ]
        for i, (ntype, title, content) in enumerate(notifs):
            session.add(Notification(
                user_id=linsy.id, type=ntype, title=title, content=content,
                is_read=(i % 3 == 0),
                created_at=now - timedelta(hours=i * 3), updated_at=now,
            ))
        await session.flush()
        print(f"  + {len(notifs)} notifications")

        # == 10. Knowledge Bases (3) ==
        print("\n[KnowledgeBases]")
        for name, cat, status, desc in [
            ("华安保险产品知识库", "product", "active", "包含所有华安保险在售产品"),
            ("保险法规与合规指南", "regulation", "active", "保险行业相关法规"),
            ("销售技巧培训材料", "training", "draft", "销售技巧和话术培训"),
        ]:
            session.add(KnowledgeBase(
                name=name, description=desc, category=cat,
                status=status, is_public=True, version=1,
                created_at=now, updated_at=now,
            ))
        await session.flush()
        print("  + 3 knowledge bases")

        # == 11. Conversations (3) ==
        print("\n[Conversations]")
        for title, ctype in [
            ("产品咨询：重疾险与医疗险区别", "product_qa"),
            ("客户张明华需求分析对话", "product_qa"),
            ("年金险方案设计讨论", "product_qa"),
        ]:
            session.add(Conversation(
                user_id=linsy.id, title=title, type=ctype,
                context=json.dumps({}), message_count=0,
                created_at=now - timedelta(hours=2), updated_at=now,
            ))
        await session.flush()
        print("  + 3 conversations")

        # == 12. Achievements (12) ==
        print("\n[Achievements]")
        achievements = [
            ("first_sale", "首单突破", "完成第一笔销售", "sales"),
            ("ten_customers", "十客达人", "累计服务10位客户", "service"),
            ("training_master", "训练达人", "完成50次陪练", "training"),
            ("script_expert", "话术专家", "创建20条优质话术", "knowledge"),
            ("community_star", "社区之星", "帖子累计100赞", "community"),
            ("learning_path", "学习达人", "完成所有基础课程", "learning"),
            ("compliance_champion", "合规先锋", "连续30天零合规问题", "compliance"),
            ("team_leader", "团队领袖", "带领团队完成月度目标", "team"),
            ("customer_service", "服务之星", "客户满意度达95%", "service"),
            ("knowledge_contributor", "知识贡献者", "贡献10篇优质帖子", "knowledge"),
            ("quick_responder", "快速响应", "平均跟进时间<2小时", "service"),
            ("year_star", "年度之星", "年度业绩Top10", "sales"),
        ]
        for code, name, desc, cat in achievements:
            session.add(UserAchievement(
                user_id=linsy.id, achievement_code=code, achievement_name=name,
                description=desc, category=cat,
                is_unlocked=(code in ["first_sale", "ten_customers", "community_star"]),
                unlocked_at=now if code in ["first_sale", "ten_customers", "community_star"] else None,
                progress=5, target=10,
                created_at=now, updated_at=now,
            ))
        await session.flush()
        print(f"  + {len(achievements)} achievements")

        # == 13. Notification Preferences ==
        session.add(NotificationPreference(
            user_id=linsy.id,
            followup_enabled=True, system_enabled=True,
            training_enabled=True, team_enabled=True, community_enabled=True,
            created_at=now, updated_at=now,
        ))
        print("\n[NotificationPreferences] + 1")

        # == 14. Audit Logs (10) ==
        print("\n[AuditLogs]")
        for i, (action, resource, desc) in enumerate([
            ("login", "user", "用户登录"), ("view_customer", "customer", "查看客户"),
            ("create_script", "script", "创建话术"), ("start_training", "training", "开始陪练"),
            ("publish_post", "community", "发布帖子"), ("export_report", "report", "导出报表"),
            ("update_settings", "system", "更新设置"), ("review_compliance", "compliance", "审核合规"),
            ("manage_user", "user", "管理用户"), ("view_dashboard", "system", "查看看板"),
        ]):
            session.add(AuditLog(
                user_id=linsy.id, action=action, resource_type=resource,
                description=desc, detail=json.dumps({"ip": "192.168.1.100"}),
                ip_address="192.168.1.100", status="success",
                created_at=now - timedelta(hours=i), updated_at=now,
            ))
        await session.flush()
        print(f"  + 10 audit logs")

        await session.commit()

        # Stats
        print(f"\n{'='*60}")
        print("Seed Complete!")
        print(f"{'='*60}")
        counts = {}
        for tn in ["roles", "organizations", "users", "customers", "customer_tags",
                    "scripts", "training_scenarios", "community_posts", "notifications",
                    "knowledge_bases", "conversations", "user_achievements",
                    "notification_preferences", "audit_logs"]:
            r = await session.execute(text(f"SELECT COUNT(*) FROM {tn}"))
            counts[tn] = r.scalar()
        for tn, c in sorted(counts.items()):
            print(f"  {tn}: {c}")
        print(f"  TOTAL: {sum(counts.values())} records")


async def main():
    from importlib import reload
    import app.core.config as config_module
    reload(config_module)
    from app.core.config import settings as s
    print(f"DATABASE_URL = {s.DATABASE_URL}")
    print(f"DEMO_MODE = {s.DEMO_MODE}")

    engine = create_async_engine(s.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        await create_all_tables(engine)
        await seed_all_data(session_factory)
    finally:
        await engine.dispose()

    print(f"\nPhase 3 database init complete!")
    print(f"DB file: {DB_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
