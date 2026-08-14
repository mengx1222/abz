"""Dashboard 服务：概览统计、AI建议、快捷数据。

Demo 模式使用内存数据，生产模式无缝切换到数据库。
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.models.ai_log import AIRequestLog
from app.models.conversation import Conversation
from app.models.customer import Customer, CustomerFollowup, CustomerInteraction
from app.models.notification import Notification
from app.models.script import Script
from app.models.training import TrainingSession
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


def _greeting() -> str:
    """按当前时间（UTC+8）返回问候语。"""
    hour = datetime.now(timezone.utc).hour + 8  # UTC+8
    if hour < 6:
        return "凌晨好"
    if hour < 9:
        return "早上好"
    if hour < 12:
        return "上午好"
    if hour < 14:
        return "中午好"
    if hour < 17:
        return "下午好"
    if hour < 19:
        return "傍晚好"
    return "晚上好"


def _relative_time(dt) -> str:
    """生成相对时间描述（如 刚刚 / 3分钟前 / 2小时前 / 昨天 / 3天前 / 1周前）。"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # SQLite 不保留时区，按 UTC 处理（与 Postgres timestamptz 语义一致）
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    seconds = delta.total_seconds()
    if seconds < 60:
        return "刚刚"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}分钟前"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}小时前"
    days = int(hours // 24)
    if days == 1:
        return "昨天"
    if days < 7:
        return f"{days}天前"
    if days < 30:
        return f"{int(days // 7)}周前"
    return f"{int(days // 30)}个月前"


_QUICK_ACTIONS = [
    QuickAction(label="问产品", icon="🤖", path="/product-qa", color="bg-accent/10 text-accent"),
    QuickAction(label="分析客户", icon="👥", path="/customers", color="bg-success/10 text-success"),
    QuickAction(label="生成话术", icon="💬", path="/scripts", color="bg-warning/10 text-warning"),
    QuickAction(label="开始陪练", icon="🎯", path="/training", color="bg-error/10 text-error"),
]


class DashboardService:
    """Dashboard 服务。"""

    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    # ---- Public methods ----

    async def get_overview(self, user_id: uuid.UUID, user_name: str) -> DashboardOverview:
        """获取 Dashboard 概览（生产模式按用户 ID 从数据库聚合）。"""
        if settings.DEMO_MODE:
            return self._demo_get_overview(user_id, user_name)
        return await self._production_get_overview(user_id, user_name)

    async def _production_get_overview(
        self, user_id: uuid.UUID, user_name: str
    ) -> DashboardOverview:
        """生产模式：从数据库聚合 Dashboard 概览（按用户负责的客户 + 用户自身活动）。"""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        # 用户负责的客户 ID 集合
        customer_ids = list(
            (
                await self.session.execute(
                    select(Customer.id).where(
                        Customer.assigned_to == user_id,
                        Customer.is_deleted == False,
                    )
                )
            ).scalars().all()
        )

        async def _count(q):
            return (await self.session.execute(q)).scalar() or 0

        # ---- today_stats ----
        inter_today = 0
        inter_yesterday = 0
        closed_count = 0
        high_intent = 0
        pending_followups = 0
        if customer_ids:
            inter_today = await _count(
                select(func.count()).select_from(CustomerInteraction).where(
                    CustomerInteraction.customer_id.in_(customer_ids),
                    func.date(CustomerInteraction.created_at) == today_str,
                )
            )
            inter_yesterday = await _count(
                select(func.count()).select_from(CustomerInteraction).where(
                    CustomerInteraction.customer_id.in_(customer_ids),
                    func.date(CustomerInteraction.created_at) == yesterday_str,
                )
            )
            closed_count = await _count(
                select(func.count()).select_from(Customer).where(
                    Customer.id.in_(customer_ids),
                    Customer.current_stage == "closed_won",
                )
            )
            high_intent = await _count(
                select(func.count()).select_from(Customer).where(
                    Customer.id.in_(customer_ids),
                    Customer.intention_level >= 4,
                )
            )
            pending_followups = await _count(
                select(func.count()).select_from(CustomerFollowup).where(
                    CustomerFollowup.customer_id.in_(customer_ids),
                    CustomerFollowup.status == "pending",
                )
            )

        ai_today = await _count(
            select(func.count()).select_from(AIRequestLog).where(
                AIRequestLog.user_id == user_id,
                func.date(AIRequestLog.created_at) == today_str,
            )
        )
        unread = await _count(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_deleted == False,
            )
        )

        inter_diff = inter_today - inter_yesterday
        inter_trend = "up" if inter_diff > 0 else ("down" if inter_diff < 0 else "neutral")
        today_stats = [
            TodayStat(
                label="今日互动", value=str(inter_today),
                sub=("+" if inter_diff > 0 else "") + str(inter_diff) + " 较昨日",
                trend=inter_trend,
            ),
            TodayStat(label="成交保单", value=str(closed_count), sub=f"{high_intent}个高意向", trend="neutral"),
            TodayStat(label="待跟进客户", value=str(pending_followups), sub="待处理跟进", trend="neutral"),
            TodayStat(label="AI 问答次数", value=str(ai_today), sub="今日累计", trend="neutral"),
        ]

        # ---- ai_suggestions（从真实数据推导） ----
        suggestions: list[AiSuggestion] = []
        if pending_followups:
            suggestions.append(AiSuggestion(
                id=str(uuid.uuid4()), title="有客户待跟进",
                description=f"您有 {pending_followups} 个待跟进客户，建议尽快安排回访。",
                tag="紧急跟进", tag_variant="error", action_url="/customers", created_at=now,
            ))
        if high_intent:
            suggestions.append(AiSuggestion(
                id=str(uuid.uuid4()), title="高意向客户跟进",
                description=f"您有 {high_intent} 个高意向客户（意向度≥4），建议优先跟进。",
                tag="高意向", tag_variant="warning", action_url="/customers", created_at=now,
            ))
        if unread:
            suggestions.append(AiSuggestion(
                id=str(uuid.uuid4()), title="查看新通知",
                description=f"您有 {unread} 条未读通知待查看。",
                tag="通知", tag_variant="default", action_url="/notifications", created_at=now,
            ))
        recent_training = (
            await self.session.execute(
                select(TrainingSession).where(
                    TrainingSession.user_id == user_id,
                    TrainingSession.status == "completed",
                ).order_by(TrainingSession.completed_at.desc()).limit(1)
            )
        ).scalars().first()
        if recent_training is not None:
            suggestions.append(AiSuggestion(
                id=str(uuid.uuid4()), title="继续 AI 陪练",
                description="坚持每天训练，提升销售技能。",
                tag="成长", tag_variant="success", action_url="/training", created_at=now,
            ))

        # ---- recent_activities（合并最近互动/陪练/话术/问答） ----
        activities: list[dict] = []
        if customer_ids:
            inter_rows = (
                await self.session.execute(
                    select(CustomerInteraction, Customer)
                    .join(Customer, CustomerInteraction.customer_id == Customer.id)
                    .where(CustomerInteraction.customer_id.in_(customer_ids))
                    .order_by(CustomerInteraction.created_at.desc())
                    .limit(5)
                )
            ).all()
            for row, cust in inter_rows:
                activities.append({
                    "type": "followup",
                    "title": f"互动：{cust.name}",
                    "description": row.content or f"互动类型 {row.type}",
                    "time": _relative_time(row.created_at),
                    "icon": "📞",
                    "ts": row.created_at,
                })
        for t in (
            await self.session.execute(
                select(TrainingSession).where(
                    TrainingSession.user_id == user_id,
                    TrainingSession.status == "completed",
                ).order_by(TrainingSession.completed_at.desc()).limit(3)
            )
        ).scalars().all():
            activities.append({
                "type": "training",
                "title": "完成AI陪练",
                "description": "训练评分已生成",
                "time": _relative_time(t.completed_at),
                "icon": "🎯",
                "ts": t.completed_at,
            })
        for s in (
            await self.session.execute(
                select(Script).where(Script.created_by == user_id)
                .order_by(Script.created_at.desc()).limit(3)
            )
        ).scalars().all():
            activities.append({
                "type": "ai_query",
                "title": "AI话术生成",
                "description": s.title,
                "time": _relative_time(s.created_at),
                "icon": "💬",
                "ts": s.created_at,
            })
        for c in (
            await self.session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
                .order_by(Conversation.created_at.desc()).limit(3)
            )
        ).scalars().all():
            activities.append({
                "type": "ai_query",
                "title": "AI产品问答",
                "description": c.title or "",
                "time": _relative_time(c.created_at),
                "icon": "🤖",
                "ts": c.created_at,
            })
        activities.sort(key=lambda a: (a["ts"] is None, a["ts"]), reverse=True)
        recent_activities = [
            RecentActivity(
                id=str(uuid.uuid4()), type=a["type"], title=a["title"],
                description=a["description"], time=a["time"], icon=a["icon"],
            )
            for a in activities[:8]
        ]

        return DashboardOverview(
            greeting=_greeting(),
            user_name=user_name,
            today_stats=today_stats,
            ai_suggestions=suggestions[:4],
            quick_actions=_QUICK_ACTIONS,
            recent_activities=recent_activities,
            unread_notifications=unread,
        )

    # ---- Demo methods ----

    def _demo_get_overview(self, user_id: uuid.UUID, user_name: str) -> DashboardOverview:
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
            quick_actions=_QUICK_ACTIONS,
            recent_activities=[RecentActivity(**a) for a in _DEMO_RECENT_ACTIVITIES],
            unread_notifications=3,
        )
