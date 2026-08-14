"""通知中心服务：通知列表、已读、设置偏好。

Demo 模式使用内存数据，生产模式无缝切换到数据库。
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.repositories.notification_repo import NotificationRepository, NotificationPreferenceRepository
from app.schemas.notification import (
    MarkReadResponse,
    NotificationItem,
    NotificationListResponse,
    NotificationPreference,
    NotificationPreferencesResponse,
    UpdatePreferenceRequest,
)

logger = get_logger()

# ---- Demo 数据 ----

_DEMO_NOTIFICATIONS: list[dict] = [
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000001")),
        "type": "followup",
        "title": "王丽华的续保即将到期",
        "content": "客户重疾险将于30天后到期，建议本周内联系续保。AI已生成续保话术，点击查看。",
        "time": "10分钟前",
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=10),
        "read": False,
        "action_url": "/customers",
        "metadata": {"customer_name": "王丽华", "product": "重疾险"},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000002")),
        "type": "system",
        "title": "新版重疾险产品上线",
        "content": "公司发布了2025版重疾险产品，新增特定疾病额外赔付和心脑血管二次赔付。请尽快完成产品学习。",
        "time": "1小时前",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "read": False,
        "action_url": "/growth",
        "metadata": {"product_version": "2025"},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000003")),
        "type": "training",
        "title": "完成今日AI陪练目标",
        "content": "您今天还有1次AI陪练未完成。坚持每天训练，提升销售技能。今日推荐场景：医疗险异议处理。",
        "time": "2小时前",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "read": False,
        "action_url": "/training",
        "metadata": {"recommended_scenario": "medical_objection"},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000004")),
        "type": "team",
        "title": "张伟分享了一篇销售心得",
        "content": "团队主管张伟分享了《如何用三个问题快速了解客户需求》，获得289个赞，快去看看吧！",
        "time": "3小时前",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=3),
        "read": True,
        "action_url": "/community",
        "metadata": {"post_id": "10000001-0001-4000-8000-000000000001"},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000005")),
        "type": "followup",
        "title": "李先生对医疗险有兴趣",
        "content": "上周咨询过百万医疗险的客户李先生，AI分析其家庭情况推荐了家庭版方案，建议今日回访。",
        "time": "5小时前",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=5),
        "read": True,
        "action_url": "/customers",
        "metadata": {"customer_name": "李先生", "product": "百万医疗险"},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000006")),
        "type": "achievement",
        "title": "恭喜获得「社区之星」成就",
        "content": "您的社区帖子累计获得100个赞，成功解锁「社区之星」成就！继续分享优质内容吧。",
        "time": "昨天",
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
        "read": True,
        "action_url": "/growth",
        "metadata": {"achievement_id": "ach-006"},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000007")),
        "type": "system",
        "title": "系统维护通知",
        "content": "系统将于本周六凌晨2:00-4:00进行升级维护，届时将暂停服务。请提前保存工作内容。",
        "time": "昨天",
        "created_at": datetime.now(timezone.utc) - timedelta(days=1, hours=6),
        "read": True,
        "action_url": None,
        "metadata": {},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000008")),
        "type": "training",
        "title": "培训课程更新提醒",
        "content": "《重疾险产品知识进阶》课程已更新第13课「产品组合方案设计」，请及时学习。",
        "time": "2天前",
        "created_at": datetime.now(timezone.utc) - timedelta(days=2),
        "read": True,
        "action_url": "/growth",
        "metadata": {"course_id": "course-001", "lesson_id": "l13"},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000009")),
        "type": "team",
        "title": "本月团队销售目标进度",
        "content": "销售一组本月已完成保费目标的78%，距离月底还有12天。加油冲刺！",
        "time": "3天前",
        "created_at": datetime.now(timezone.utc) - timedelta(days=3),
        "read": True,
        "action_url": None,
        "metadata": {"team_progress": 78},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000010")),
        "type": "followup",
        "title": "赵女士待跟进提醒",
        "content": "赵女士的方案报价已发送3天，建议跟进确认。AI分析认为成交概率较高（意向度4星）。",
        "time": "3天前",
        "created_at": datetime.now(timezone.utc) - timedelta(days=3),
        "read": True,
        "action_url": "/customers",
        "metadata": {"customer_name": "赵女士", "intent_level": 4},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000011")),
        "type": "system",
        "title": "合规知识更新",
        "content": "银保监会发布了新的销售行为合规管理办法解读，请及时学习并在话术中注意规避新增的违规情形。",
        "time": "5天前",
        "created_at": datetime.now(timezone.utc) - timedelta(days=5),
        "read": True,
        "action_url": "/scripts",
        "metadata": {},
    },
    {
        "id": str(uuid.UUID("30000001-0001-4000-8000-000000000012")),
        "type": "achievement",
        "title": "恭喜获得「成交先锋」成就",
        "content": "您本月成功签下首单，解锁「成交先锋」成就！继续努力冲击业绩冠军。",
        "time": "1周前",
        "created_at": datetime.now(timezone.utc) - timedelta(days=7),
        "read": True,
        "action_url": "/growth",
        "metadata": {"achievement_id": "ach-005"},
    },
]

_DEMO_PREFERENCES: list[dict] = [
    {"type": "followup", "label": "客户跟进提醒", "enabled": True, "channel": ["in_app", "push"]},
    {"type": "system", "label": "系统通知", "enabled": True, "channel": ["in_app"]},
    {"type": "training", "label": "训练提醒", "enabled": True, "channel": ["in_app", "push"]},
    {"type": "team", "label": "团队动态", "enabled": True, "channel": ["in_app"]},
    {"type": "achievement", "label": "成就通知", "enabled": True, "channel": ["in_app", "push"]},
]

# ---- 生产模式偏好类型映射（与前端 5 类偏好一致） ----
# 模型 notification_preferences 是单行多布尔列；community_enabled 对应前端/业务上的
# "achievement（成就通知）" 偏好。
_PREF_LABELS: dict[str, str] = {
    "followup": "客户跟进提醒",
    "system": "系统通知",
    "training": "训练提醒",
    "team": "团队动态",
    "achievement": "成就通知",
}
_PREF_CHANNELS: dict[str, list[str]] = {
    "followup": ["in_app", "push"],
    "system": ["in_app"],
    "training": ["in_app", "push"],
    "team": ["in_app"],
    "achievement": ["in_app", "push"],
}
_PREF_COLUMN: dict[str, str] = {
    "followup": "followup_enabled",
    "system": "system_enabled",
    "training": "training_enabled",
    "team": "team_enabled",
    "achievement": "community_enabled",
}


def _build_preferences(
    followup: bool,
    system: bool,
    training: bool,
    team: bool,
    achievement: bool,
) -> list[NotificationPreference]:
    """根据模型布尔列构建前端期望的 5 类偏好。"""
    values = {
        "followup": followup,
        "system": system,
        "training": training,
        "team": team,
        "achievement": achievement,
    }
    return [
        NotificationPreference(
            type=t,
            label=_PREF_LABELS[t],
            enabled=values[t],
            channel=_PREF_CHANNELS[t],
        )
        for t in ("followup", "system", "training", "team", "achievement")
    ]


def _relative_time(dt) -> str:
    """生成相对时间描述（如 刚刚 / 3分钟前 / 2小时前 / 昨天 / 3天前 / 1周前）。"""
    if dt is None:
        return ""
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


class NotificationService:
    """通知中心服务。"""

    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    # ---- Public methods ----

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        type_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> NotificationListResponse:
        """获取通知列表（生产模式按用户 ID 查询数据库）。"""
        if settings.DEMO_MODE:
            return self._demo_list_notifications(user_id, type_filter, page, page_size)

        repo = NotificationRepository(self.session)
        items, total = await repo.list_by_user(
            user_id, page=page, page_size=page_size, type_filter=type_filter
        )
        unread = await repo.unread_count(user_id)
        return NotificationListResponse(
            notifications=[
                NotificationItem(
                    id=str(n.id),
                    type=n.type or "system",
                    title=n.title or "",
                    content=n.content or "",
                    time=_relative_time(n.created_at),
                    created_at=n.created_at or datetime.now(timezone.utc),
                    read=bool(n.is_read),
                    action_url=n.action_url,
                    metadata=n.metadata_ or {},
                )
                for n in items
            ],
            total=total,
            unread_count=unread,
            page=page,
            page_size=page_size,
        )

    async def mark_read(
        self,
        user_id: uuid.UUID,
        notification_ids: list[str] | None = None,
        read_all: bool = False,
    ) -> MarkReadResponse:
        """标记通知已读（生产模式按用户 ID 更新数据库）。"""
        if settings.DEMO_MODE:
            return self._demo_mark_read(user_id, notification_ids, read_all)

        repo = NotificationRepository(self.session)
        ids = [uuid.UUID(i) for i in notification_ids] if notification_ids and not read_all else None
        try:
            if read_all:
                count = await repo.mark_read(user_id)
            elif ids:
                count = await repo.mark_read(user_id, ids)
            else:
                count = 0
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return MarkReadResponse(updated_count=count)

    async def get_preferences(self, user_id: uuid.UUID) -> NotificationPreferencesResponse:
        """获取通知偏好设置（生产模式从数据库单行偏好读取）。"""
        if settings.DEMO_MODE:
            return self._demo_get_preferences(user_id)

        repo = NotificationPreferenceRepository(self.session)
        pref = await repo.get_by_user(user_id)
        if pref is None:
            # 无偏好记录时返回默认（全部启用）
            return NotificationPreferencesResponse(
                preferences=_build_preferences(True, True, True, True, True)
            )
        return NotificationPreferencesResponse(
            preferences=_build_preferences(
                pref.followup_enabled,
                pref.system_enabled,
                pref.training_enabled,
                pref.team_enabled,
                pref.community_enabled,
            )
        )

    async def update_preference(
        self, user_id: uuid.UUID, req: UpdatePreferenceRequest
    ) -> NotificationPreference:
        """更新通知偏好设置（生产模式写入对应布尔列）。"""
        if settings.DEMO_MODE:
            return self._demo_update_preference(user_id, req)

        column = _PREF_COLUMN.get(req.type)
        if column is None:
            raise ValueError(f"Unknown notification type: {req.type}")
        enabled = req.enabled if req.enabled is not None else True

        repo = NotificationPreferenceRepository(self.session)
        pref = await repo.get_by_user(user_id)
        if pref is None:
            await repo.create(user_id=user_id, **{column: enabled})
        else:
            setattr(pref, column, enabled)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return NotificationPreference(
            type=req.type,
            label=_PREF_LABELS.get(req.type, req.type),
            enabled=enabled,
            channel=req.channel or _PREF_CHANNELS.get(req.type, ["in_app"]),
        )

    # ---- Demo methods ----

    def _demo_list_notifications(
        self,
        user_id: uuid.UUID,
        type_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> NotificationListResponse:
        """Demo：获取通知列表。"""
        items = list(_DEMO_NOTIFICATIONS)
        if type_filter and type_filter != "all":
            items = [n for n in items if n["type"] == type_filter]
        total = len(items)
        unread = sum(1 for n in items if not n["read"])
        start = (page - 1) * page_size
        end = start + page_size
        paged = items[start:end]
        return NotificationListResponse(
            notifications=[NotificationItem(**n) for n in paged],
            total=total,
            unread_count=unread,
            page=page,
            page_size=page_size,
        )

    def _demo_mark_read(
        self,
        user_id: uuid.UUID,
        notification_ids: list[str] | None = None,
        read_all: bool = False,
    ) -> MarkReadResponse:
        """Demo：标记通知已读。"""
        count = 0
        if read_all:
            for n in _DEMO_NOTIFICATIONS:
                if not n["read"]:
                    n["read"] = True
                    count += 1
        elif notification_ids:
            id_set = set(notification_ids)
            for n in _DEMO_NOTIFICATIONS:
                if n["id"] in id_set and not n["read"]:
                    n["read"] = True
                    count += 1
        return MarkReadResponse(updated_count=count)

    def _demo_get_preferences(self, user_id: uuid.UUID) -> NotificationPreferencesResponse:
        """Demo：获取通知偏好设置。"""
        return NotificationPreferencesResponse(
            preferences=[NotificationPreference(**p) for p in _DEMO_PREFERENCES]
        )

    def _demo_update_preference(self, user_id: uuid.UUID, req: UpdatePreferenceRequest) -> NotificationPreference:
        """Demo：更新通知偏好设置。"""
        for p in _DEMO_PREFERENCES:
            if p["type"] == req.type:
                if req.enabled is not None:
                    p["enabled"] = req.enabled
                if req.channel is not None:
                    p["channel"] = req.channel
                return NotificationPreference(**p)
        raise ValueError(f"Unknown notification type: {req.type}")
