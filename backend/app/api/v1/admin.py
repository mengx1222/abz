"""管理后台 API —— 用户管理/合规中心/审计日志/数据看板/系统设置/社区管理/话术管理/陪练场景管理。

所有端点均需管理员权限 (require_role)。
Demo 模式使用内存数据，不依赖数据库。
"""
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from structlog import get_logger

from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserItem,
    AdminDisableRequest,
    AuditLogItem,
    OverviewStats,
    AiUsageStats,
    TrainingStats,
    CommunityStats,
    ComplianceRuleCreate,
    ComplianceRuleUpdate,
    ComplianceRuleItem,
    ComplianceReviewItem,
    ComplianceReviewProcess,
    AdminPostItem,
    PinRequest,
    RecommendRequest,
    AdminScriptItem,
    ScriptApproveRequest,
    ScenarioCreate,
    ScenarioUpdate,
    AdminScenarioItem,
    SystemSettings,
    SystemSettingsUpdate,
)
from app.schemas.common import PaginatedResponse, SuccessResponse

logger = get_logger()

router = APIRouter()

# ============================================================
# DEMO DATA — 所有管理后台内存数据
# ============================================================

# 用户列表 (Demo)
_DEMO_USERS = [
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000001")),
        "phone": "13800138000",
        "name": "林思远",
        "role_code": "AGENT",
        "role_name": "代理人",
        "organization_name": "上海分公司-浦东团队",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "created_at": datetime.now(timezone.utc) - timedelta(days=120),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000002")),
        "phone": "13800138001",
        "name": "张伟",
        "role_code": "TEAM_LEADER",
        "role_name": "团队长",
        "organization_name": "上海分公司-浦东团队",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(minutes=30),
        "created_at": datetime.now(timezone.utc) - timedelta(days=200),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000003")),
        "phone": "13800138002",
        "name": "李芳",
        "role_code": "BRANCH_ADMIN",
        "role_name": "分公司管理员",
        "organization_name": "上海分公司",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(days=1),
        "created_at": datetime.now(timezone.utc) - timedelta(days=300),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000004")),
        "phone": "13800138003",
        "name": "王强",
        "role_code": "SYSTEM_ADMIN",
        "role_name": "系统管理员",
        "organization_name": "华安保险总部",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(minutes=5),
        "created_at": datetime.now(timezone.utc) - timedelta(days=365),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000005")),
        "phone": "13900001111",
        "name": "陈小明",
        "role_code": "AGENT",
        "role_name": "代理人",
        "organization_name": "上海分公司-浦东团队",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(hours=8),
        "created_at": datetime.now(timezone.utc) - timedelta(days=90),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000006")),
        "phone": "13900002222",
        "name": "刘婷",
        "role_code": "AGENT",
        "role_name": "代理人",
        "organization_name": "上海分公司-浦西团队",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(days=3),
        "created_at": datetime.now(timezone.utc) - timedelta(days=60),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000007")),
        "phone": "13900003333",
        "name": "赵磊",
        "role_code": "TEAM_LEADER",
        "role_name": "团队长",
        "organization_name": "上海分公司-浦西团队",
        "team_name": None,
        "status": "disabled",
        "last_login_at": datetime.now(timezone.utc) - timedelta(days=30),
        "created_at": datetime.now(timezone.utc) - timedelta(days=180),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000008")),
        "phone": "13900004444",
        "name": "孙晓峰",
        "role_code": "KNOWLEDGE_ADMIN",
        "role_name": "知识管理员",
        "organization_name": "华安保险总部",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(hours=12),
        "created_at": datetime.now(timezone.utc) - timedelta(days=150),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000009")),
        "phone": "13900005555",
        "name": "周美玲",
        "role_code": "COMPLIANCE",
        "role_name": "合规专员",
        "organization_name": "华安保险总部",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(days=2),
        "created_at": datetime.now(timezone.utc) - timedelta(days=240),
    },
    {
        "id": str(uuid.UUID("10000000-0000-0000-0000-000000000010")),
        "phone": "13900006666",
        "name": "吴浩然",
        "role_code": "HQ_ADMIN",
        "role_name": "总部管理员",
        "organization_name": "华安保险总部",
        "team_name": None,
        "status": "active",
        "last_login_at": datetime.now(timezone.utc) - timedelta(minutes=45),
        "created_at": datetime.now(timezone.utc) - timedelta(days=270),
    },
]

# 审计日志 (Demo)
_DEMO_AUDIT_LOGS = []
for _i in range(50):
    actions = [
        ("login", "system", "用户登录"),
        ("customer.view", "customer", "查看客户详情"),
        ("customer.create", "customer", "创建客户"),
        ("customer.update", "customer", "更新客户阶段"),
        ("ai.product_qa", "ai", "AI产品问答"),
        ("script.generate", "script", "生成话术"),
        ("training.start", "training", "开始陪练训练"),
        ("community.post", "community", "发布社区帖子"),
        ("knowledge.view", "knowledge", "查看知识文档"),
        ("compliance.check", "compliance", "执行合规检查"),
    ]
    action, rtype, desc = actions[_i % len(actions)]
    user = _DEMO_USERS[_i % len(_DEMO_USERS)]
    _DEMO_AUDIT_LOGS.append({
        "id": f"audit_{_i + 1:04d}",
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user["role_code"],
        "action": action,
        "resource_type": rtype,
        "resource_id": f"res_{uuid.uuid4().hex[:8]}",
        "description": desc,
        "ip_address": f"192.168.{_i % 5}.{100 + _i}",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=_i * 2),
    })

# 合规规则 (Demo)
_DEMO_COMPLIANCE_RULES = [
    {
        "id": "rule_001",
        "name": "收益承诺禁止",
        "description": "禁止在话术中使用确定性的收益承诺表述",
        "category": "regulatory",
        "severity": "violation",
        "severity_label": "违规",
        "keywords": ["保证收益", "稳赚不赔", "一定赚钱", "承诺回报"],
        "patterns": ["收益.*保证", "回报.*确定"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=180),
    },
    {
        "id": "rule_002",
        "name": "绝对化表达限制",
        "description": "禁止使用绝对化用语描述产品优势",
        "category": "regulatory",
        "severity": "warning",
        "severity_label": "警告",
        "keywords": ["最好", "唯一", "100%赔付", "绝对安全"],
        "patterns": ["最好.*保险", "唯一.*选择"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=180),
    },
    {
        "id": "rule_003",
        "name": "不当理赔承诺",
        "description": "不得承诺确定性的理赔结果",
        "category": "regulatory",
        "severity": "violation",
        "severity_label": "违规",
        "keywords": ["一定赔", "秒赔", "100%赔付"],
        "patterns": ["一定.*赔", "肯定.*赔付"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=150),
    },
    {
        "id": "rule_004",
        "name": "夸大保障范围",
        "description": "不得夸大产品的保障范围或赔付能力",
        "category": "regulatory",
        "severity": "violation",
        "severity_label": "违规",
        "keywords": ["什么都能报", "无限报销", "全部报销"],
        "patterns": ["什么.*都能报", "无限.*报销"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=120),
    },
    {
        "id": "rule_005",
        "name": "诱导销售检测",
        "description": "检测施压式和诱导式销售话术",
        "category": "sales_practice",
        "severity": "warning",
        "severity_label": "警告",
        "keywords": ["不买就没了", "最后机会", "仅限今天"],
        "patterns": ["不买.*就.*没了", "最后.*机会"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=90),
    },
    {
        "id": "rule_006",
        "name": "竞品贬低检测",
        "description": "禁止不当对比或贬低竞品",
        "category": "sales_practice",
        "severity": "warning",
        "severity_label": "警告",
        "keywords": ["碾压", "吊打", "秒杀", "甩几条街"],
        "patterns": ["比.*好多了", "碾压"],
        "is_active": False,
        "created_at": datetime.now(timezone.utc) - timedelta(days=60),
    },
]

# 合规审核列表 (Demo)
_DEMO_COMPLIANCE_REVIEWS = [
    {
        "id": "review_001",
        "type": "script",
        "type_label": "话术审核",
        "title": "百万医疗险首次面谈话术",
        "content_preview": "张先生您好，我们安诊保百万医疗险可以保证您100%赔付...",
        "author_name": "林思远",
        "severity": "violation",
        "status": "pending",
        "priority": "high",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=3),
        "reviewed_by": None,
        "reviewed_at": None,
    },
    {
        "id": "review_002",
        "type": "community_post",
        "type_label": "社区帖子审核",
        "title": "如何用3句话让客户理解免赔额",
        "content_preview": "大家好，分享一下我最近总结的免赔额沟通技巧...",
        "author_name": "陈小明",
        "severity": "warning",
        "status": "pending",
        "priority": "medium",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=8),
        "reviewed_by": None,
        "reviewed_at": None,
    },
    {
        "id": "review_003",
        "type": "script",
        "type_label": "话术审核",
        "title": "重疾险异议处理话术 — 价格异议",
        "content_preview": "客户可能会觉得保费高，但您可以这样引导...",
        "author_name": "刘婷",
        "severity": "warning",
        "status": "approved",
        "priority": "low",
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
        "reviewed_by": "周美玲",
        "reviewed_at": datetime.now(timezone.utc) - timedelta(hours=20),
    },
    {
        "id": "review_004",
        "type": "community_post",
        "type_label": "社区帖子审核",
        "title": "理赔案例分享 — 慢性病客户成功获赔",
        "content_preview": "分享一个我最近处理的理赔案例，客户有高血压但成功理赔...",
        "author_name": "张伟",
        "severity": "violation",
        "status": "rejected",
        "priority": "high",
        "created_at": datetime.now(timezone.utc) - timedelta(days=2),
        "reviewed_by": "周美玲",
        "reviewed_at": datetime.now(timezone.utc) - timedelta(days=1),
    },
    {
        "id": "review_005",
        "type": "script",
        "type_label": "话术审核",
        "title": "年金险养老规划话术",
        "content_preview": "王女士您好，关于养老金规划，我可以为您详细分析...",
        "author_name": "林思远",
        "severity": "warning",
        "status": "pending",
        "priority": "medium",
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=30),
        "reviewed_by": None,
        "reviewed_at": None,
    },
]

# 管理后台帖子 (Demo)
_DEMO_ADMIN_POSTS = [
    {
        "id": uuid.uuid4(),
        "title": "我是如何用3句话让客户理解免赔额的",
        "author_name": "陈小明",
        "category": "experience",
        "category_label": "实战经验",
        "status": "published",
        "views_count": 1200,
        "likes_count": 56,
        "comments_count": 23,
        "is_pinned": True,
        "is_recommended": True,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
    },
    {
        "id": uuid.uuid4(),
        "title": "百万医疗险 vs 重疾险 完整对比分析",
        "author_name": "张伟",
        "category": "knowledge",
        "category_label": "知识分享",
        "status": "published",
        "views_count": 890,
        "likes_count": 42,
        "comments_count": 15,
        "is_pinned": False,
        "is_recommended": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
    },
    {
        "id": uuid.uuid4(),
        "title": "新人在犹豫期内的应对技巧",
        "author_name": "刘婷",
        "category": "discussion",
        "category_label": "讨论",
        "status": "published",
        "views_count": 650,
        "likes_count": 28,
        "comments_count": 11,
        "is_pinned": False,
        "is_recommended": False,
        "created_at": datetime.now(timezone.utc) - timedelta(days=2),
    },
    {
        "id": uuid.uuid4(),
        "title": "老年客户保险需求深度分析",
        "author_name": "林思远",
        "category": "knowledge",
        "category_label": "知识分享",
        "status": "published",
        "views_count": 540,
        "likes_count": 35,
        "comments_count": 8,
        "is_pinned": False,
        "is_recommended": False,
        "created_at": datetime.now(timezone.utc) - timedelta(days=3),
    },
    {
        "id": uuid.uuid4(),
        "title": "客户说\u2018保险都是骗人的\u2019怎么回应？",
        "author_name": "陈小明",
        "category": "discussion",
        "category_label": "讨论",
        "status": "published",
        "views_count": 2100,
        "likes_count": 89,
        "comments_count": 45,
        "is_pinned": True,
        "is_recommended": False,
        "created_at": datetime.now(timezone.utc) - timedelta(days=5),
    },
    {
        "id": uuid.uuid4(),
        "title": "理赔案例分享 — 慢性病客户获赔经历",
        "author_name": "张伟",
        "category": "experience",
        "category_label": "实战经验",
        "status": "reported",
        "views_count": 320,
        "likes_count": 12,
        "comments_count": 5,
        "is_pinned": False,
        "is_recommended": False,
        "created_at": datetime.now(timezone.utc) - timedelta(days=2),
    },
]

# 管理后台话术 (Demo)
_DEMO_ADMIN_SCRIPTS = [
    {
        "id": "scr_001",
        "title": "百万医疗险 — 首次面谈话术",
        "style": "professional",
        "style_label": "专业型",
        "product_type": "百万医疗险",
        "content_preview": "张先生您好，感谢您抽出时间了解我们的保险产品。我根据您的家庭情况，为您整理了一份保障方案...",
        "author_name": "林思远",
        "status": "approved",
        "compliance_status": "GREEN",
        "usage_count": 28,
        "favorite_count": 12,
        "created_at": datetime.now(timezone.utc) - timedelta(days=5),
    },
    {
        "id": "scr_002",
        "title": "重疾险 — 价格异议处理",
        "style": "affinity",
        "style_label": "亲和型",
        "product_type": "重疾险",
        "content_preview": "我非常理解您的顾虑，保费确实是一笔不小的支出。不过我们可以换个角度来考虑这个问题...",
        "author_name": "陈小明",
        "status": "approved",
        "compliance_status": "GREEN",
        "usage_count": 45,
        "favorite_count": 18,
        "created_at": datetime.now(timezone.utc) - timedelta(days=3),
    },
    {
        "id": "scr_003",
        "title": "意外险 — 短信邀约话术",
        "style": "concise",
        "style_label": "简洁型",
        "product_type": "意外险",
        "content_preview": "王女士您好，我是华安保险的林思远。近期我们推出了一款性价比很高的意外险...",
        "author_name": "林思远",
        "status": "pending",
        "compliance_status": "YELLOW",
        "usage_count": 0,
        "favorite_count": 0,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=6),
    },
    {
        "id": "scr_004",
        "title": "年金险 — 养老规划话术",
        "style": "data_driven",
        "style_label": "数据驱动型",
        "product_type": "年金险",
        "content_preview": "根据国家统计局数据，我国人均预期寿命已达78.6岁...",
        "author_name": "刘婷",
        "status": "pending",
        "compliance_status": "YELLOW",
        "usage_count": 0,
        "favorite_count": 0,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
    },
    {
        "id": "scr_005",
        "title": "寿险 — 家庭保障话术",
        "style": "affinity",
        "style_label": "亲和型",
        "product_type": "寿险",
        "content_preview": "李先生您好，作为一个家庭的顶梁柱，您的保障规划关系到全家人的未来...",
        "author_name": "陈小明",
        "status": "rejected",
        "compliance_status": "RED",
        "usage_count": 0,
        "favorite_count": 0,
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
    },
    {
        "id": "scr_006",
        "title": "车险续保 — 电话沟通话术",
        "style": "concise",
        "style_label": "简洁型",
        "product_type": "车险",
        "content_preview": "张先生您好，我是华安保险的客户经理，您的车险即将到期，为您做了续保方案...",
        "author_name": "刘婷",
        "status": "approved",
        "compliance_status": "GREEN",
        "usage_count": 67,
        "favorite_count": 22,
        "created_at": datetime.now(timezone.utc) - timedelta(days=7),
    },
]

# 管理后台陪练场景 (Demo)
_DEMO_ADMIN_SCENARIOS = [
    {
        "id": "scn_admin_001",
        "title": "首次面谈 — 百万医疗险",
        "description": "练习首次面谈沟通技巧",
        "category": "initial_contact",
        "difficulty": "easy",
        "status": "published",
        "duration_minutes": 8,
        "usage_count": 312,
        "avg_score": 78.5,
        "tags": ["百万医疗", "首次面谈", "入门"],
        "created_at": datetime.now(timezone.utc) - timedelta(days=60),
    },
    {
        "id": "scn_admin_002",
        "title": "价格异议 — 重疾险",
        "description": "应对客户对重疾险价格的异议",
        "category": "objection_handling",
        "difficulty": "medium",
        "status": "published",
        "duration_minutes": 12,
        "usage_count": 245,
        "avg_score": 72.3,
        "tags": ["重疾险", "价格异议", "进阶"],
        "created_at": datetime.now(timezone.utc) - timedelta(days=55),
    },
    {
        "id": "scn_admin_003",
        "title": "竞品对比 — 意外险",
        "description": "应对客户将产品与竞品对比",
        "category": "objection_handling",
        "difficulty": "hard",
        "status": "published",
        "duration_minutes": 15,
        "usage_count": 189,
        "avg_score": 68.1,
        "tags": ["意外险", "竞品对比", "挑战"],
        "created_at": datetime.now(timezone.utc) - timedelta(days=50),
    },
    {
        "id": "scn_admin_004",
        "title": "客户投诉处理",
        "description": "处理客户对理赔速度的投诉",
        "category": "complaint_handling",
        "difficulty": "hard",
        "status": "published",
        "duration_minutes": 15,
        "usage_count": 156,
        "avg_score": 65.7,
        "tags": ["投诉处理", "理赔", "挑战"],
        "created_at": datetime.now(timezone.utc) - timedelta(days=45),
    },
    {
        "id": "scn_admin_005",
        "title": "健康告知引导",
        "description": "帮助客户正确填写健康告知",
        "category": "compliance",
        "difficulty": "medium",
        "status": "draft",
        "duration_minutes": 10,
        "usage_count": 0,
        "avg_score": 0.0,
        "tags": ["健康告知", "合规", "进阶"],
        "created_at": datetime.now(timezone.utc) - timedelta(days=5),
    },
]

# 系统设置 (Demo)
_DEMO_SETTINGS = SystemSettings(
    ai={
        "default_model": "deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.7,
        "timeout_seconds": 30,
        "rate_limit_per_minute": 20,
    },
    rag={
        "embedding_model": "text-embedding-3-small",
        "default_chunk_size": 512,
        "default_chunk_overlap": 50,
        "top_k": 5,
        "similarity_threshold": 0.7,
    },
    compliance={
        "auto_check_enabled": True,
        "severity_levels": ["warning", "violation"],
        "auto_reject_violations": True,
    },
    notification={
        "follow_up_reminder_hours": 24,
        "inactive_customer_days": 30,
    },
    community={
        "post_review_enabled": True,
        "max_tags_per_post": 5,
        "comment_max_length": 500,
    },
)


# ============================================================
# Helper
# ============================================================

def _paginated(items: list, page: int, page_size: int):
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return PaginatedResponse.create(items[start:end], total, page, page_size)


# ============================================================
# 9.1 用户管理
# ============================================================

@router.get("/users")
async def list_users(
    keyword: str = Query("", description="搜索姓名/手机号"),
    role: str = Query("", description="角色筛选"),
    status: str = Query("", description="状态: active/disabled"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN", "TEAM_LEADER"
    ])),
):
    """获取用户列表。"""
    items = list(_DEMO_USERS)
    if keyword:
        items = [u for u in items if keyword in u["name"] or keyword in u["phone"]]
    if role:
        items = [u for u in items if u["role_code"] == role]
    if status:
        items = [u for u in items if u["status"] == status]
    return _paginated(items, page, page_size)


@router.post("/users")
async def create_user(
    body: AdminUserCreate,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """创建用户。"""
    new_user = {
        "id": str(uuid.uuid4()),
        "phone": body.phone,
        "name": body.name,
        "role_code": body.role_code,
        "role_name": body.role_code,
        "organization_name": "",
        "team_name": None,
        "status": "active",
        "last_login_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    _DEMO_USERS.append(new_user)
    return SuccessResponse(data=new_user, message="用户创建成功")


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN"])),
):
    """更新用户。"""
    for u in _DEMO_USERS:
        if u["id"] == user_id:
            if body.name is not None:
                u["name"] = body.name
            if body.role_code is not None:
                u["role_code"] = body.role_code
                u["role_name"] = body.role_code
            return SuccessResponse(data=u, message="用户更新成功")
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    body: AdminDisableRequest,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """禁用用户。"""
    for u in _DEMO_USERS:
        if u["id"] == user_id:
            u["status"] = "disabled"
            return SuccessResponse(
                data={"id": u["id"], "status": "disabled", "reason": body.reason},
                message="用户已禁用",
            )
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})


@router.post("/users/{user_id}/enable")
async def enable_user(
    user_id: str,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """启用用户。"""
    for u in _DEMO_USERS:
        if u["id"] == user_id:
            u["status"] = "active"
            return SuccessResponse(data={"id": u["id"], "status": "active"}, message="用户已启用")
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})


# ============================================================
# 9.2 审计日志
# ============================================================

@router.get("/audit-logs")
async def list_audit_logs(
    user_id: str = Query("", description="操作人ID"),
    action: str = Query("", description="操作类型"),
    resource_type: str = Query("", description="资源类型"),
    start_time: str = Query("", description="开始时间(ISO 8601)"),
    end_time: str = Query("", description="结束时间(ISO 8601)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN", "COMPLIANCE"
    ])),
):
    """查询审计日志。"""
    items = list(_DEMO_AUDIT_LOGS)
    if user_id:
        items = [i for i in items if i["user_id"] == user_id]
    if action:
        items = [i for i in items if i["action"] == action]
    if resource_type:
        items = [i for i in items if i["resource_type"] == resource_type]
    # 按时间倒序
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return _paginated(items, page, page_size)


# ============================================================
# 9.3 数据看板
# ============================================================

@router.get("/analytics/overview")
async def analytics_overview(
    period: str = Query("month", description="统计周期: week/month/quarter/year"),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN", "TEAM_LEADER"
    ])),
):
    """总览数据。"""
    data = OverviewStats(
        period=period,
        user_stats={
            "total_users": len(_DEMO_USERS),
            "active_users": len([u for u in _DEMO_USERS if u["status"] == "active"]),
            "new_users": 3,
            "active_rate": 90.0,
        },
        customer_stats={
            "total_customers": 12580,
            "new_customers": 856,
            "high_intent": 1245,
            "conversion_rate": 15.3,
        },
        ai_stats={
            "total_interactions": 8934,
            "satisfaction_rate": 86.2,
            "avg_response_time_ms": 1200,
        },
        training_stats={
            "total_sessions": 1234,
            "avg_score": 76.8,
            "completion_rate": 82.5,
        },
        community_stats={
            "total_posts": 234,
            "total_comments": 1567,
            "active_contributors": 89,
        },
    )
    return SuccessResponse(data=data)


@router.get("/analytics/ai-usage")
async def analytics_ai_usage(
    period: str = Query("month"),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN"
    ])),
):
    """AI 使用分析。"""
    data = AiUsageStats(
        period=period,
        total_calls=8934,
        feature_breakdown=[
            {"feature": "product_qa", "count": 3560, "percentage": 39.9, "label": "产品问答"},
            {"feature": "script_generate", "count": 2340, "percentage": 26.2, "label": "话术生成"},
            {"feature": "customer_analysis", "count": 1780, "percentage": 19.9, "label": "客户分析"},
            {"feature": "training", "count": 1254, "percentage": 14.0, "label": "陪练训练"},
        ],
        top_users=[
            {"user_id": "10000000-0000-0000-0000-000000000001", "name": "林思远", "usage_count": 156},
            {"user_id": "10000000-0000-0000-0000-000000000005", "name": "陈小明", "usage_count": 134},
            {"user_id": "10000000-0000-0000-0000-000000000006", "name": "刘婷", "usage_count": 112},
        ],
        error_rate=2.3,
        avg_latency_ms=1200,
        token_usage={
            "total_input_tokens": 4500000,
            "total_output_tokens": 2300000,
            "total_tokens": 6800000,
        },
    )
    return SuccessResponse(data=data)


@router.get("/analytics/training")
async def analytics_training(
    period: str = Query("month"),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN"
    ])),
):
    """训练分析。"""
    data = TrainingStats(
        period=period,
        total_sessions=1234,
        avg_score=76.8,
        completion_rate=82.5,
        scenario_popularity=[
            {"scenario": "首次面谈", "count": 312},
            {"scenario": "价格异议", "count": 245},
            {"scenario": "竞品对比", "count": 189},
            {"scenario": "客户投诉", "count": 156},
            {"scenario": "促成签约", "count": 134},
        ],
        score_distribution=[
            {"range": "90-100", "count": 124},
            {"range": "80-89", "count": 356},
            {"range": "70-79", "count": 412},
            {"range": "60-69", "count": 234},
            {"range": "0-59", "count": 108},
        ],
    )
    return SuccessResponse(data=data)


@router.get("/analytics/community")
async def analytics_community(
    period: str = Query("month"),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN"
    ])),
):
    """社区分析。"""
    data = CommunityStats(
        period=period,
        total_posts=234,
        total_comments=1567,
        active_contributors=89,
        category_distribution=[
            {"category": "实战经验", "count": 78, "percentage": 33.3},
            {"category": "知识分享", "count": 56, "percentage": 23.9},
            {"category": "讨论", "count": 45, "percentage": 19.2},
            {"category": "求助提问", "count": 32, "percentage": 13.7},
            {"category": "优秀话术", "count": 23, "percentage": 9.8},
        ],
        top_posts=[
            {"title": "客户说'保险都是骗人的'怎么回应？", "views": 2100, "likes": 89},
            {"title": "我是如何用3句话让客户理解免赔额的", "views": 1200, "likes": 56},
            {"title": "百万医疗险 vs 重疾险 完整对比分析", "views": 890, "likes": 42},
        ],
    )
    return SuccessResponse(data=data)


# ============================================================
# 9.4 合规中心
# ============================================================

@router.get("/compliance/rules")
async def list_compliance_rules(
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "COMPLIANCE"
    ])),
):
    """合规规则列表。"""
    return SuccessResponse(data=_DEMO_COMPLIANCE_RULES)


@router.post("/compliance/rules")
async def create_compliance_rule(
    body: ComplianceRuleCreate,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN", "COMPLIANCE"])),
):
    """创建合规规则。"""
    rule = body.model_copy()
    rule.id = f"rule_{uuid.uuid4().hex[:8]}"
    rule.created_at = datetime.now(timezone.utc)
    _DEMO_COMPLIANCE_RULES.append(rule.model_dump())
    return SuccessResponse(data=rule, message="规则创建成功")


@router.put("/compliance/rules/{rule_id}")
async def update_compliance_rule(
    rule_id: str,
    body: ComplianceRuleUpdate,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN", "COMPLIANCE"])),
):
    """更新合规规则。"""
    for r in _DEMO_COMPLIANCE_RULES:
        if r["id"] == rule_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                r[k] = v
            return SuccessResponse(data=r, message="规则更新成功")
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "规则不存在"})


@router.get("/compliance/reviews")
async def list_compliance_reviews(
    status: str = Query("", description="状态: pending/approved/rejected"),
    type: str = Query("", description="类型: script/community_post"),
    priority: str = Query("", description="优先级: high/medium/low"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN", "COMPLIANCE"
    ])),
):
    """合规审核列表。"""
    items = list(_DEMO_COMPLIANCE_REVIEWS)
    if status:
        items = [i for i in items if i["status"] == status]
    if type:
        items = [i for i in items if i["type"] == type]
    if priority:
        items = [i for i in items if i["priority"] == priority]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return _paginated(items, page, page_size)


@router.post("/compliance/reviews/{review_id}/process")
async def process_compliance_review(
    review_id: str,
    body: ComplianceReviewProcess,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN", "COMPLIANCE"])),
):
    """处理合规审核。"""
    for r in _DEMO_COMPLIANCE_REVIEWS:
        if r["id"] == review_id:
            r["status"] = body.action
            r["reviewed_by"] = current_user.name
            r["reviewed_at"] = datetime.now(timezone.utc)
            return SuccessResponse(data=r, message=f"审核已{body.action}")
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "审核记录不存在"})


# ============================================================
# 9.5 社区管理
# ============================================================

@router.get("/community/posts")
async def list_admin_posts(
    status: str = Query("", description="状态: published/pending_review/hidden/reported"),
    category: str = Query("", description="分类"),
    keyword: str = Query("", description="搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN"
    ])),
):
    """管理视角帖子列表。"""
    items = list(_DEMO_ADMIN_POSTS)
    if status:
        items = [i for i in items if i["status"] == status]
    if category:
        items = [i for i in items if i["category"] == category]
    if keyword:
        items = [i for i in items if keyword in i["title"]]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return _paginated(items, page, page_size)


@router.post("/community/posts/{post_id}/pin")
async def toggle_pin_post(
    post_id: str,
    body: PinRequest,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """置顶/取消置顶帖子。"""
    for p in _DEMO_ADMIN_POSTS:
        if str(p["id"]) == post_id:
            p["is_pinned"] = body.is_pinned
            return SuccessResponse(data={"id": post_id, "is_pinned": body.is_pinned})
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "帖子不存在"})


@router.post("/community/posts/{post_id}/recommend")
async def toggle_recommend_post(
    post_id: str,
    body: RecommendRequest,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """推荐/取消推荐帖子。"""
    for p in _DEMO_ADMIN_POSTS:
        if str(p["id"]) == post_id:
            p["is_recommended"] = body.is_recommended
            return SuccessResponse(data={"id": post_id, "is_recommended": body.is_recommended})
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "帖子不存在"})


@router.delete("/community/posts/{post_id}")
async def delete_admin_post(
    post_id: str,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """删除帖子（管理操作）。"""
    for i, p in enumerate(_DEMO_ADMIN_POSTS):
        if str(p["id"]) == post_id:
            _DEMO_ADMIN_POSTS.pop(i)
            return SuccessResponse(data={"id": post_id}, message="帖子已删除")
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "帖子不存在"})


# ============================================================
# 9.6 话术库管理
# ============================================================

@router.get("/scripts")
async def list_admin_scripts(
    status: str = Query("", description="审核状态: pending/approved/rejected"),
    keyword: str = Query("", description="搜索"),
    style: str = Query("", description="风格筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN"
    ])),
):
    """管理视角话术列表。"""
    items = list(_DEMO_ADMIN_SCRIPTS)
    if status:
        items = [i for i in items if i["status"] == status]
    if keyword:
        items = [i for i in items if keyword in i["title"] or keyword in i["content_preview"]]
    if style:
        items = [i for i in items if i["style"] == style]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return _paginated(items, page, page_size)


@router.post("/scripts/{script_id}/approve")
async def approve_script(
    script_id: str,
    body: ScriptApproveRequest,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN", "COMPLIANCE"])),
):
    """审批话术。"""
    for s in _DEMO_ADMIN_SCRIPTS:
        if s["id"] == script_id:
            s["status"] = body.action
            return SuccessResponse(
                data={
                    "id": script_id,
                    "status": body.action,
                    "reviewed_by": current_user.name,
                    "comment": body.comment,
                },
                message=f"话术已{body.action}",
            )
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "话术不存在"})


# ============================================================
# 9.7 陪练场景管理
# ============================================================

@router.get("/training/scenarios")
async def list_admin_scenarios(
    status: str = Query("", description="状态: published/draft"),
    category: str = Query("", description="分类"),
    difficulty: str = Query("", description="难度"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role([
        "SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN"
    ])),
):
    """陪练场景管理列表。"""
    items = list(_DEMO_ADMIN_SCENARIOS)
    if status:
        items = [i for i in items if i["status"] == status]
    if category:
        items = [i for i in items if i["category"] == category]
    if difficulty:
        items = [i for i in items if i["difficulty"] == difficulty]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return _paginated(items, page, page_size)


@router.post("/training/scenarios")
async def create_scenario(
    body: ScenarioCreate,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """创建陪练场景。"""
    scenario = {
        "id": f"scn_{uuid.uuid4().hex[:12]}",
        "title": body.title,
        "description": body.description,
        "category": body.category,
        "difficulty": body.difficulty,
        "status": "draft",
        "duration_minutes": body.estimated_duration_minutes,
        "usage_count": 0,
        "avg_score": 0.0,
        "tags": body.tags,
        "created_at": datetime.now(timezone.utc),
    }
    _DEMO_ADMIN_SCENARIOS.append(scenario)
    return SuccessResponse(data=scenario, message="场景创建成功")


@router.put("/training/scenarios/{scenario_id}")
async def update_scenario(
    scenario_id: str,
    body: ScenarioUpdate,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """更新陪练场景。"""
    for s in _DEMO_ADMIN_SCENARIOS:
        if s["id"] == scenario_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                if k == "estimated_duration_minutes":
                    s["duration_minutes"] = v
                else:
                    s[k] = v
            return SuccessResponse(data=s, message="场景更新成功")
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "场景不存在"})


@router.post("/training/scenarios/{scenario_id}/publish")
async def publish_scenario(
    scenario_id: str,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """发布陪练场景。"""
    for s in _DEMO_ADMIN_SCENARIOS:
        if s["id"] == scenario_id:
            s["status"] = "published"
            return SuccessResponse(data={"id": scenario_id, "status": "published"}, message="场景已发布")
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "场景不存在"})


@router.delete("/training/scenarios/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """删除陪练场景。"""
    for i, s in enumerate(_DEMO_ADMIN_SCENARIOS):
        if s["id"] == scenario_id:
            _DEMO_ADMIN_SCENARIOS.pop(i)
            return SuccessResponse(data={"id": scenario_id}, message="场景已删除")
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "场景不存在"})


# ============================================================
# 9.8 系统设置
# ============================================================

@router.get("/settings")
async def get_settings(
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """获取系统设置。"""
    return SuccessResponse(data=_DEMO_SETTINGS)


@router.put("/settings")
async def update_settings(
    body: SystemSettingsUpdate,
    current_user: User = Depends(require_role(["SYSTEM_ADMIN", "HQ_ADMIN"])),
):
    """更新系统设置。"""
    updated_keys = []
    for section in ["ai", "rag", "compliance", "notification", "community"]:
        val = getattr(body, section, None)
        if val is not None:
            setattr(_DEMO_SETTINGS, section, val)
            updated_keys.extend([f"{section}.{k}" for k in val.keys()])
    return SuccessResponse(data={"updated_keys": updated_keys}, message="系统设置已更新")
