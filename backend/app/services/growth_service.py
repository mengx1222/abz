"""成长体系服务：统计数据、能力评估、学习进度、排行榜、成就系统。

Demo 模式使用内存数据，生产模式无缝切换到数据库。
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.repositories.notification_repo import UserAchievementRepository
from app.schemas.growth import (
    AchievementItem,
    AchievementList,
    AbilityScore,
    CourseDetail,
    GrowthOverview,
    LeaderboardItem,
    LeaderboardResponse,
    LearningCourse,
    MonthlyStatItem,
    WeeklyTrendItem,
)

logger = get_logger()

# ---- Demo 数据 ----

_DEMO_MONTHLY_STATS: list[dict] = [
    {"label": "本月通话量", "value": "186", "unit": "通", "change": "+12%", "up": True},
    {"label": "转化率", "value": "14.2", "unit": "%", "change": "+2.3%", "up": True},
    {"label": "成交保单", "value": "26", "unit": "件", "change": "+5", "up": True},
    {"label": "保费收入", "value": "12.8", "unit": "万", "change": "+3.2万", "up": True},
]

_DEMO_WEEKLY_TREND: list[dict] = [
    {"day": "周一", "calls": 32, "deals": 3},
    {"day": "周二", "calls": 28, "deals": 5},
    {"day": "周三", "calls": 35, "deals": 4},
    {"day": "周四", "calls": 30, "deals": 2},
    {"day": "周五", "calls": 38, "deals": 6},
    {"day": "周六", "calls": 15, "deals": 4},
    {"day": "周日", "calls": 8, "deals": 2},
]

_DEMO_ABILITY_SCORES: list[dict] = [
    {"label": "产品知识", "score": 82},
    {"label": "沟通技巧", "score": 75},
    {"label": "异议处理", "score": 68},
    {"label": "需求分析", "score": 88},
    {"label": "促成能力", "score": 60},
    {"label": "客户维护", "score": 72},
]

_DEMO_LEARNING_COURSES: list[dict] = [
    {
        "id": "course-001",
        "title": "重疾险产品知识进阶",
        "progress": 85,
        "total": "12/14 课",
        "status": "进行中",
        "category": "产品知识",
        "description": "深入学习重疾险产品条款、保障范围、理赔条件，掌握核心卖点。",
        "total_lessons": 14,
        "completed_lessons": 12,
        "lessons": [
            {"id": "l1", "title": "重疾险概述与发展趋势", "completed": True, "duration": "15min"},
            {"id": "l2", "title": "核心保障责任解读", "completed": True, "duration": "20min"},
            {"id": "l3", "title": "等待期与免责条款", "completed": True, "duration": "18min"},
            {"id": "l4", "title": "轻症/中症赔付标准", "completed": True, "duration": "22min"},
            {"id": "l5", "title": "特定疾病额外赔付", "completed": True, "duration": "15min"},
            {"id": "l6", "title": "心脑血管二次赔付", "completed": True, "duration": "20min"},
            {"id": "l7", "title": "保费豁免条款详解", "completed": True, "duration": "18min"},
            {"id": "l8", "title": "健康告知与核保要点", "completed": True, "duration": "25min"},
            {"id": "l9", "title": "理赔流程与案例", "completed": True, "duration": "30min"},
            {"id": "l10", "title": "竞品对比分析", "completed": True, "duration": "20min"},
            {"id": "l11", "title": "常见客户异议Q&A", "completed": True, "duration": "22min"},
            {"id": "l12", "title": "销售话术与促成技巧", "completed": True, "duration": "25min"},
            {"id": "l13", "title": "产品组合方案设计", "completed": False, "duration": "28min"},
            {"id": "l14", "title": "综合案例实战演练", "completed": False, "duration": "35min"},
        ],
    },
    {
        "id": "course-002",
        "title": "电销黄金开场白技巧",
        "progress": 100,
        "total": "8/8 课",
        "status": "已完成",
        "category": "销售技巧",
        "description": "掌握电销开场白的5种高转化模式，提升接通后黄金30秒的沟通效率。",
        "total_lessons": 8,
        "completed_lessons": 8,
        "lessons": [
            {"id": "l1", "title": "开场白的重要性与黄金30秒", "completed": True, "duration": "12min"},
            {"id": "l2", "title": "亲近型开场白话术", "completed": True, "duration": "15min"},
            {"id": "l3", "title": "专业型开场白话术", "completed": True, "duration": "18min"},
            {"id": "l4", "title": "关怀型开场白话术", "completed": True, "duration": "14min"},
            {"id": "l5", "title": "新闻型开场白话术", "completed": True, "duration": "16min"},
            {"id": "l6", "title": "社交型开场白话术", "completed": True, "duration": "15min"},
            {"id": "l7", "title": "语音语调与节奏控制", "completed": True, "duration": "20min"},
            {"id": "l8", "title": "实战录音分析与点评", "completed": True, "duration": "25min"},
        ],
    },
    {
        "id": "course-003",
        "title": "高净值客户经营方法",
        "progress": 40,
        "total": "4/10 课",
        "status": "进行中",
        "category": "客户经营",
        "description": "学习高净值客户的识别、触达、维护和转化全流程经营方法。",
        "total_lessons": 10,
        "completed_lessons": 4,
        "lessons": [
            {"id": "l1", "title": "高净值客户画像分析", "completed": True, "duration": "20min"},
            {"id": "l2", "title": "触达渠道与破冰策略", "completed": True, "duration": "25min"},
            {"id": "l3", "title": "信任建立的关键动作", "completed": True, "duration": "22min"},
            {"id": "l4", "title": "需求挖掘深度访谈", "completed": True, "duration": "30min"},
            {"id": "l5", "title": "资产配置方案设计", "completed": False, "duration": "28min"},
            {"id": "l6", "title": "风险隔离与传承规划", "completed": False, "duration": "25min"},
            {"id": "l7", "title": "异议处理与关系维护", "completed": False, "duration": "22min"},
            {"id": "l8", "title": "转介绍裂变策略", "completed": False, "duration": "20min"},
            {"id": "l9", "title": "客户分级管理体系", "completed": False, "duration": "18min"},
            {"id": "l10", "title": "综合案例实战演练", "completed": False, "duration": "35min"},
        ],
    },
    {
        "id": "course-004",
        "title": "保险法规与合规销售",
        "progress": 100,
        "total": "6/6 课",
        "status": "已完成",
        "category": "合规知识",
        "description": "系统学习保险相关法律法规，掌握合规销售的红线与最佳实践。",
        "total_lessons": 6,
        "completed_lessons": 6,
        "lessons": [
            {"id": "l1", "title": "保险法核心条款解读", "completed": True, "duration": "20min"},
            {"id": "l2", "title": "销售行为合规管理办法", "completed": True, "duration": "25min"},
            {"id": "l3", "title": "消费者权益保护要点", "completed": True, "duration": "18min"},
            {"id": "l4", "title": "常见违规案例警示", "completed": True, "duration": "22min"},
            {"id": "l5", "title": "合规销售话术规范", "completed": True, "duration": "20min"},
            {"id": "l6", "title": "合规自检与风险防控", "completed": True, "duration": "15min"},
        ],
    },
    {
        "id": "course-005",
        "title": "百万医疗险深度解析",
        "progress": 20,
        "total": "2/10 课",
        "status": "进行中",
        "category": "产品知识",
        "description": "全面解析百万医疗险的产品设计、理赔实务与销售策略。",
        "total_lessons": 10,
        "completed_lessons": 2,
        "lessons": [
            {"id": "l1", "title": "百万医疗险市场定位", "completed": True, "duration": "15min"},
            {"id": "l2", "title": "核心保障责任解读", "completed": True, "duration": "22min"},
            {"id": "l3", "title": "免赔额与赔付比例", "completed": False, "duration": "18min"},
            {"id": "l4", "title": "保证续保条款详解", "completed": False, "duration": "20min"},
            {"id": "l5", "title": "外购药与特殊治疗", "completed": False, "duration": "16min"},
            {"id": "l6", "title": "健康告知与核保", "completed": False, "duration": "25min"},
            {"id": "l7", "title": "常见理赔案例分析", "completed": False, "duration": "28min"},
            {"id": "l8", "title": "竞品对比与差异化卖点", "completed": False, "duration": "22min"},
            {"id": "l9", "title": "客户异议处理话术", "completed": False, "duration": "20min"},
            {"id": "l10", "title": "销售场景实战演练", "completed": False, "duration": "30min"},
        ],
    },
    {
        "id": "course-006",
        "title": "意外险销售进阶课程",
        "progress": 0,
        "total": "0/8 课",
        "status": "未开始",
        "category": "产品知识",
        "description": "掌握意外险的产品特点、适用人群及搭配销售策略。",
        "total_lessons": 8,
        "completed_lessons": 0,
        "lessons": [
            {"id": "l1", "title": "意外险市场分析", "completed": False, "duration": "12min"},
            {"id": "l2", "title": "保障责任与除外责任", "completed": False, "duration": "18min"},
            {"id": "l3", "title": "职业分类与费率", "completed": False, "duration": "15min"},
            {"id": "l4", "title": "搭配销售策略", "completed": False, "duration": "20min"},
            {"id": "l5", "title": "场景化销售话术", "completed": False, "duration": "22min"},
            {"id": "l6", "title": "理赔实务案例", "completed": False, "duration": "25min"},
            {"id": "l7", "title": "常见客户Q&A", "completed": False, "duration": "18min"},
            {"id": "l8", "title": "实战演练与考核", "completed": False, "duration": "30min"},
        ],
    },
]

_DEMO_LEADERBOARD: list[dict] = [
    {"rank": 1, "user_name": "陈明辉", "org_name": "华东区第一营业部·销售一组", "score": 2850, "avatar": "CM"},
    {"rank": 2, "user_name": "刘婷婷", "org_name": "华东区第一营业部·销售二组", "score": 2680, "avatar": "LT"},
    {"rank": 3, "user_name": "张伟", "org_name": "华东区第一营业部·管理", "score": 2540, "avatar": "ZW"},
    {"rank": 4, "user_name": "赵志强", "org_name": "华东区第二营业部·销售一组", "score": 2310, "avatar": "ZZ"},
    {"rank": 5, "user_name": "林思远", "org_name": "华东区第一营业部·销售一组", "score": 2180, "avatar": "LS"},
    {"rank": 6, "user_name": "孙丽娜", "org_name": "华东区第二营业部·销售二组", "score": 2050, "avatar": "SL"},
    {"rank": 7, "user_name": "王大力", "org_name": "华东区第一营业部·销售二组", "score": 1920, "avatar": "WD"},
    {"rank": 8, "user_name": "李芳", "org_name": "华安保险总部", "score": 1880, "avatar": "LF"},
    {"rank": 9, "user_name": "黄小燕", "org_name": "华东区第二营业部·销售一组", "score": 1750, "avatar": "HX"},
    {"rank": 10, "user_name": "吴建国", "org_name": "华东区第二营业部·销售二组", "score": 1620, "avatar": "WJ"},
]

_DEMO_ACHIEVEMENTS: list[dict] = [
    {"id": "ach-001", "name": "初出茅庐", "description": "完成首次AI产品问答", "icon": "🌱", "is_unlocked": True, "category": "AI互动",
     "unlocked_at": datetime.now(timezone.utc) - timedelta(days=30)},
    {"id": "ach-002", "name": "话术新星", "description": "生成10条AI话术", "icon": "✨", "is_unlocked": True, "category": "AI互动",
     "unlocked_at": datetime.now(timezone.utc) - timedelta(days=25)},
    {"id": "ach-003", "name": "陪练达人", "description": "完成5次AI陪练训练", "icon": "🎯", "is_unlocked": True, "category": "AI互动",
     "unlocked_at": datetime.now(timezone.utc) - timedelta(days=20)},
    {"id": "ach-004", "name": "知识探客", "description": "浏览知识库文章50篇", "icon": "📚", "is_unlocked": True, "category": "学习成长",
     "unlocked_at": datetime.now(timezone.utc) - timedelta(days=15)},
    {"id": "ach-005", "name": "成交先锋", "description": "当月成交首单", "icon": "🏆", "is_unlocked": True, "category": "业绩里程碑",
     "unlocked_at": datetime.now(timezone.utc) - timedelta(days=10)},
    {"id": "ach-006", "name": "社区之星", "description": "发布帖子获得100赞", "icon": "⭐", "is_unlocked": True, "category": "社区贡献",
     "unlocked_at": datetime.now(timezone.utc) - timedelta(days=5)},
    {"id": "ach-007", "name": "全能代理人", "description": "六维能力评分全部超过70分", "icon": "💎", "is_unlocked": False, "category": "综合能力", "unlocked_at": None},
    {"id": "ach-008", "name": "百日连冠", "description": "连续100天使用系统", "icon": "🔥", "is_unlocked": False, "category": "持续学习", "unlocked_at": None},
    {"id": "ach-009", "name": "分享达人", "description": "在社区分享10篇优质内容", "icon": "🤝", "is_unlocked": False, "category": "社区贡献", "unlocked_at": None},
    {"id": "ach-010", "name": "业绩冠军", "description": "月度保费收入排名Top 3", "icon": "👑", "is_unlocked": False, "category": "业绩里程碑", "unlocked_at": None},
    {"id": "ach-011", "name": "合规标兵", "description": "连续30天话术合规率100%", "icon": "🛡️", "is_unlocked": False, "category": "合规建设", "unlocked_at": None},
    {"id": "ach-012", "name": "帮带导师", "description": "帮助3位新人完成首次陪练", "icon": "🎓", "is_unlocked": False, "category": "团队贡献", "unlocked_at": None},
]


class GrowthService:
    """成长体系服务。"""

    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    # ---- Public methods ----

    async def get_overview(self, user_phone: str) -> GrowthOverview:
        """获取成长概览数据。"""
        if settings.DEMO_MODE:
            return self._demo_get_overview(user_phone)

        # Production path — returns minimal placeholder data
        return GrowthOverview(
            monthly_stats=[],
            weekly_trend=[],
            ability_scores=[],
            learning_courses=[],
            level=1,
            level_name="代理人",
            exp_current=0,
            exp_next=100,
            total_exp=0,
        )

    async def get_course_detail(self, course_id: str, user_phone: str) -> CourseDetail | None:
        """获取课程详情。"""
        if settings.DEMO_MODE:
            return self._demo_get_course_detail(course_id, user_phone)

        # Production path — placeholder
        return None

    async def get_leaderboard(self, period: str = "month", user_phone: str = "") -> LeaderboardResponse:
        """获取排行榜。"""
        if settings.DEMO_MODE:
            return self._demo_get_leaderboard(period, user_phone)

        # Production path — empty leaderboard
        return LeaderboardResponse(
            period=period,
            leaderboard=[],
            my_rank=None,
        )

    async def get_achievements(self, user_phone: str) -> AchievementList:
        """获取成就列表。"""
        if settings.DEMO_MODE:
            return self._demo_get_achievements(user_phone)

        # Production path — query via repository
        repo = UserAchievementRepository(self.session)
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")  # TODO: resolve from user_phone
        rows = await repo.list_by_user(user_id)
        unlocked = []
        locked = []
        for r in rows:
            item = AchievementItem(
                id=str(r.id),
                name=r.achievement_name or "",
                description="",
                icon="🏅",
                is_unlocked=bool(r.is_unlocked),
                category="",
                unlocked_at=r.created_at,
            )
            if item.is_unlocked:
                unlocked.append(item)
            else:
                locked.append(item)
        return AchievementList(unlocked=unlocked, locked=locked)

    # ---- Demo methods ----

    def _demo_get_overview(self, user_phone: str) -> GrowthOverview:
        """Demo：获取成长概览数据。"""
        return GrowthOverview(
            monthly_stats=[MonthlyStatItem(**s) for s in _DEMO_MONTHLY_STATS],
            weekly_trend=[WeeklyTrendItem(**s) for s in _DEMO_WEEKLY_TREND],
            ability_scores=[AbilityScore(**s) for s in _DEMO_ABILITY_SCORES],
            learning_courses=[LearningCourse(**c) for c in _DEMO_LEARNING_COURSES],
            level=5,
            level_name="资深代理人",
            exp_current=2180,
            exp_next=3000,
            total_exp=8200,
        )

    def _demo_get_course_detail(self, course_id: str, user_phone: str) -> CourseDetail | None:
        """Demo：获取课程详情。"""
        for c in _DEMO_LEARNING_COURSES:
            if c["id"] == course_id:
                return CourseDetail(**c)
        return None

    def _demo_get_leaderboard(self, period: str = "month", user_phone: str = "") -> LeaderboardResponse:
        """Demo：获取排行榜。"""
        leaderboard = [LeaderboardItem(**item) for item in _DEMO_LEADERBOARD]
        my_rank = None
        for item in leaderboard:
            if item.user_name == "林思远":
                my_rank = item
                break
        return LeaderboardResponse(
            period=period,
            leaderboard=leaderboard,
            my_rank=my_rank,
        )

    def _demo_get_achievements(self, user_phone: str) -> AchievementList:
        """Demo：获取成就列表。"""
        unlocked = []
        locked = []
        for a in _DEMO_ACHIEVEMENTS:
            item = AchievementItem(**a)
            if item.is_unlocked:
                unlocked.append(item)
            else:
                locked.append(item)
        return AchievementList(unlocked=unlocked, locked=locked)
