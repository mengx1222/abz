"""Dashboard 服务：概览统计、AI建议、快捷数据。

Demo 模式使用内存数据，生产模式无缝切换到数据库。
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.schemas.dashboard import (
    AiSuggestion,
    DashboardOverview,
    QuickAction,
    RecentActivity,
    TodayStat,
)

logger = get_logger()

# ---- Demo 数据 ----

_DEMO_TODAY_STATS: list[dict] = [
    {"label": "今日通话", "value": "12", "sub": "+3 较昨日", "trend": "up"},
    {"label": "成交保单", "value": "2", "sub": "+1 较昨日", "trend": "up"},
    {"label": "待跟进客户", "value": "8", "sub": "3个高意向", "trend": "neutral"},
    {"label": "AI 问答次数", "value": "34", "sub": "产品 18 · 话术 16", "trend": "neutral"},
]

_DEMO_AI_SUGGESTIONS: list[dict] = [
    {
        "id": str(uuid.UUID("40000001-0001-4000-8000-000000000001")),
        "title": "王女士的续保即将到期",
        "description": "客户重疾险将于30天后到期，建议本周内联系续保，可推荐升级方案。",
        "tag": "紧急跟进",
        "tag_variant": "error",
        "action_url": "/customers",
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=30),
    },
    {
        "id": str(uuid.UUID("40000001-0001-4000-8000-000000000002")),
        "title": "李先生对医疗险有兴趣",
        "description": "上周咨询过百万医疗险，AI分析其家庭情况推荐了家庭版方案，建议今日回访。",
        "tag": "高意向",
        "tag_variant": "warning",
        "action_url": "/customers",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
    },
    {
        "id": str(uuid.UUID("40000001-0001-4000-8000-000000000003")),
        "title": "新版重疾险产品培训",
        "description": "公司刚发布了新版重疾险产品，建议花10分钟了解核心卖点变化。",
        "tag": "学习",
        "tag_variant": "default",
        "action_url": "/growth",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=4),
    },
    {
        "id": str(uuid.UUID("40000001-0001-4000-8000-000000000004")),
        "title": "本周陪练成绩提升中",
        "description": "本周AI陪练综合评分75分，较上周提升5分。建议加强「促成能力」训练。",
        "tag": "成长",
        "tag_variant": "success",
        "action_url": "/training",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=6),
    },
]

_DEMO_RECENT_ACTIVITIES: list[dict] = [
    {
        "id": str(uuid.UUID("40000002-0001-4000-8000-000000000001")),
        "type": "call",
        "title": "完成客户通话",
        "description": "与赵女士通话15分钟，讨论重疾险方案",
        "time": "20分钟前",
        "icon": "📞",
    },
    {
        "id": str(uuid.UUID("40000002-0001-4000-8000-000000000002")),
        "type": "deal",
        "title": "成功签单",
        "description": "刘先生投保百万医疗险，年缴保费1280元",
        "time": "2小时前",
        "icon": "🎉",
    },
    {
        "id": str(uuid.UUID("40000002-0001-4000-8000-000000000003")),
        "type": "ai_query",
        "title": "AI产品问答",
        "description": "查询了「安诊保尊享版的等待期是多长」",
        "time": "3小时前",
        "icon": "🤖",
    },
    {
        "id": str(uuid.UUID("40000002-0001-4000-8000-000000000004")),
        "type": "training",
        "title": "完成AI陪练",
        "description": "场景：医疗险异议处理，综合评分78分",
        "time": "4小时前",
        "icon": "🎯",
    },
    {
        "id": str(uuid.UUID("40000002-0001-4000-8000-000000000005")),
        "type": "followup",
        "title": "客户跟进记录",
        "description": "跟进王丽华续保意向，客户表示周末考虑",
        "time": "5小时前",
        "icon": "📝",
    },
    {
        "id": str(uuid.UUID("40000002-0001-4000-8000-000000000006")),
        "type": "ai_query",
        "title": "AI话术生成",
        "description": "生成续保话术，风格：亲和型",
        "time": "昨天",
        "icon": "💬",
    },
    {
        "id": str(uuid.UUID("40000002-0001-4000-8000-000000000007")),
        "type": "deal",
        "title": "成功签单",
        "description": "周女士投保意外险，年缴保费360元",
        "time": "昨天",
        "icon": "🎉",
    },
    {
        "id": str(uuid.UUID("40000002-0001-4000-8000-000000000008")),
        "type": "call",
        "title": "完成客户通话",
        "description": "与孙先生通话22分钟，介绍年金险产品",
        "time": "昨天",
        "icon": "📞",
    },

]


class DashboardService:
    """Dashboard 服务。"""

    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    # ---- Public methods ----

    async def get_overview(self, user_phone: str, user_name: str) -> DashboardOverview:
        """获取 Dashboard 概览。"""
        if settings.DEMO_MODE:
            return self._demo_get_overview(user_phone, user_name)

        # Production path — basic structure with zeros/empty lists
        return DashboardOverview(
            greeting="你好",
            user_name=user_name,
            today_stats=[],
            ai_suggestions=[],
            quick_actions=[
                QuickAction(label="问产品", icon="🤖", path="/product-qa", color="bg-accent/10 text-accent"),
                QuickAction(label="分析客户", icon="👥", path="/customers", color="bg-success/10 text-success"),
                QuickAction(label="生成话术", icon="💬", path="/scripts", color="bg-warning/10 text-warning"),
                QuickAction(label="开始陪练", icon="🎯", path="/training", color="bg-error/10 text-error"),
            ],
            recent_activities=[],
            unread_notifications=0,
        )

    # ---- Demo methods ----

    def _demo_get_overview(self, user_phone: str, user_name: str) -> DashboardOverview:
        """Demo：获取 Dashboard 概览。"""
        hour = datetime.now(timezone.utc).hour + 8  # UTC+8
        if hour < 6:
            greeting = "凌晨好"
        elif hour < 9:
            greeting = "早上好"
        elif hour < 12:
            greeting = "上午好"
        elif hour < 14:
            greeting = "中午好"
        elif hour < 17:
            greeting = "下午好"
        elif hour < 19:
            greeting = "傍晚好"
        else:
            greeting = "晚上好"

        return DashboardOverview(
            greeting=greeting,
            user_name=user_name,
            today_stats=[TodayStat(**s) for s in _DEMO_TODAY_STATS],
            ai_suggestions=[AiSuggestion(**s) for s in _DEMO_AI_SUGGESTIONS],
            quick_actions=[
                QuickAction(label="问产品", icon="🤖", path="/product-qa", color="bg-accent/10 text-accent"),
                QuickAction(label="分析客户", icon="👥", path="/customers", color="bg-success/10 text-success"),
                QuickAction(label="生成话术", icon="💬", path="/scripts", color="bg-warning/10 text-warning"),
                QuickAction(label="开始陪练", icon="🎯", path="/training", color="bg-error/10 text-error"),
            ],
            recent_activities=[RecentActivity(**a) for a in _DEMO_RECENT_ACTIVITIES],
            unread_notifications=3,
        )
