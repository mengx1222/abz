"""社区服务：帖子/评论/点赞/收藏/AI摘要。

Demo 模式使用内存列表，生产模式无缝切换到数据库。
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.repositories.community_repo import (
    PostRepository,
    PostCommentRepository,
    PostLikeRepository,
    PostFavoriteRepository,
)
from app.schemas.community import (
    AuthorBrief,
    CommentAuthor,
    CommentCreate,
    CommentItem,
    LikeToggleResponse,
    FavoriteToggleResponse,
    PostCreate,
    PostUpdate,
    PostDetail,
    PostListItem,
)

logger = get_logger()

# ---- Demo 数据 ----

CATEGORY_LABELS: dict[str, str] = {
    "experience": "实战经验",
    "knowledge": "知识分享",
    "question": "求助提问",
    "discussion": "讨论",
    "script": "优秀话术",
}

# 固定的用户ID映射（与 DEMO_USERS_CONFIG 一致）
_DEMO_USER_IDS: dict[str, uuid.UUID] = {
    "13800138000": uuid.UUID("a1b2c3d4-0001-4000-8000-000000000001"),  # 林思远 AGENT
    "13800138001": uuid.UUID("b2c3d4e5-0002-4000-8000-000000000002"),  # 张伟 TEAM_LEADER
    "13800138002": uuid.UUID("c3d4e5f6-0003-4000-8000-000000000003"),  # 李芳 KNOWLEDGE_ADMIN
    "13800138003": uuid.UUID("d4e5f6a7-0004-4000-8000-000000000004"),  # 王强 COMPLIANCE
}

_DEMO_USER_INFO: dict[str, dict] = {
    "13800138000": {"name": "林思远", "role": "agent", "org": "华东区第一营业部"},
    "13800138001": {"name": "张伟", "role": "team_leader", "org": "华东区第一营业部"},
    "13800138002": {"name": "李芳", "role": "knowledge_admin", "org": "华安保险总部"},
    "13800138003": {"name": "王强", "role": "compliance", "org": "华安保险合规部"},
}

_DEMO_POSTS: list[dict] = [
    {
        "id": uuid.UUID("10000001-0001-4000-8000-000000000001"),
        "title": "分享：如何用三个问题快速了解客户需求",
        "content": (
            "经过大量实践，我总结了三个核心问题，可以帮助代理人快速了解客户的保障需求和预算。\n\n"
            "## 第一个问题：保障认知\n\n"
            "\"您目前有没有给自己或家人配置过商业保险呢？\"\n\n"
            "这个问题帮我判断客户是纯小白还是有基础认知。小白需要从头科普，有认知的可以聊具体方案。\n\n"
            "## 第二个问题：关注重点\n\n"
            "\"如果您现在要选一份保险，最看重的是什么？\"\n\n"
            "有人看重价格，有人看重保障范围，有人看重理赔速度。了解这个决定了我的推荐方向。\n\n"
            "## 第三个问题：预算范围\n\n"
            "\"您觉得每年花在保险上的预算大概在什么范围？\"\n\n"
            "不是直接问预算，而是给一个模糊的范围让客户选。避免一上来就报具体数字吓跑客户。\n\n"
            "通过这三个问题，我能在5分钟内锁定客户的画像，后续沟通效率提升了至少3倍。"
        ),
        "category": "experience",
        "tags": ["需求挖掘", "实战技巧", "方法论"],
        "author_phone": "13800138001",
        "views_count": 1456,
        "likes_count": 289,
        "comments_count": 67,
        "favorites_count": 45,
        "is_pinned": True,
        "is_recommended": True,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
    },
    {
        "id": uuid.UUID("10000001-0001-4000-8000-000000000002"),
        "title": "百万医疗险理赔案例复盘：甲状腺结节",
        "content": (
            "最近协助一位客户完成了甲状腺结节的百万医疗险理赔，从投保前的健康告知到术后理赔，"
            "整个流程非常顺利。\n\n"
            "## 案例背景\n\n"
            "客户王先生，42岁，2023年6月投保百万医疗险。投保时体检报告显示甲状腺结节TI-RADS 2类，"
            "我们在健康告知环节做了充分的风险评估。\n\n"
            "## 健康告知处理\n\n"
            "关键点：如实告知甲状腺结节的存在，提交完整体检报告。保险公司核保后正常承保，没有加费或除外。\n\n"
            "## 理赔经过\n\n"
            "2024年3月客户因结节增大（TI-RADS 4a）手术。术后病理为良性。\n\n"
            "理赔材料：\n"
            "- 住院发票原件\n"
            "- 病理报告\n"
            "- 出院小结\n"
            "- 手术记录\n\n"
            "理赔金额：手术费+住院费+药费共5.2万元，扣除1万免赔额，实际赔付4.2万元。\n\n"
            "## 经验总结\n\n"
            "1. 健康告知一定要如实填写，切勿隐瞒\n"
            "2. 保留好所有就医材料原件\n"
            "3. TI-RADS 2类通常不影响承保\n"
            "4. 理赔时效：从提交到打款仅7个工作日"
        ),
        "category": "experience",
        "tags": ["理赔案例", "百万医疗险", "健康告知"],
        "author_phone": "13800138003",
        "views_count": 978,
        "likes_count": 178,
        "comments_count": 43,
        "favorites_count": 62,
        "is_pinned": False,
        "is_recommended": True,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=6),
    },
    {
        "id": uuid.UUID("10000001-0001-4000-8000-000000000003"),
        "title": "每周销售心得：从\"卖保险\"到\"做顾问\"的转变",
        "content": (
            "做保险销售三年，最大的感悟就是：不要想着\"卖\"保险，而是要成为客户的\"风险顾问\"。\n\n"
            "## 思维转变\n\n"
            "以前我总是想怎么把产品推销出去，结果客户一看就抗拒。后来转变思路，"
            "先帮客户分析风险，再提供建议，成交是自然而然的结果。\n\n"
            "## 实战效果\n\n"
            "转变之后，这个月我的转化率从12%提升到了18%，客户满意度也明显提高。\n"
            "更重要的是，老客户主动介绍新客户的比例翻了一倍。\n\n"
            "## 核心方法\n\n"
            "1. 先听后说，了解客户真实需求\n"
            "2. 用案例说话，不讲空话\n"
            "3. 比较时客观公正，不踩竞品\n"
            "4. 把产品手册变成风险分析报告"
        ),
        "category": "experience",
        "tags": ["销售心得", "思维转变", "转化提升"],
        "author_phone": "13800138001",
        "views_count": 2134,
        "likes_count": 456,
        "comments_count": 89,
        "favorites_count": 78,
        "is_pinned": False,
        "is_recommended": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
    },
    {
        "id": uuid.UUID("10000001-0001-4000-8000-000000000004"),
        "title": "新人求助：第一次电销紧张怎么办？",
        "content": (
            "入职第二周，明天要开始打第一批电话了，特别紧张。\n\n"
            "前辈们有什么好的心态调整方法吗？话术背了很多遍但还是怕忘词，"
            "万一客户问到我不懂的问题怎么办？求指点！"
        ),
        "category": "question",
        "tags": ["新人提问", "电销技巧", "心态调整"],
        "author_phone": "13800138000",
        "views_count": 567,
        "likes_count": 89,
        "comments_count": 63,
        "favorites_count": 12,
        "is_pinned": False,
        "is_recommended": False,
        "created_at": datetime.now(timezone.utc) - timedelta(hours=5),
    },
    {
        "id": uuid.UUID("10000001-0001-4000-8000-000000000005"),
        "title": "分享：如何应对客户比价",
        "content": (
            "很多客户会拿其他公司的产品来比价，我的经验是不要直接否定竞品，"
            "而是帮客户建立\"对比维度\"。\n\n"
            "## 四维对比法\n\n"
            "从以下四个维度对比：\n"
            "1. 公司实力：注册资本、偿付能力\n"
            "2. 理赔时效：平均理赔天数\n"
            "3. 服务网点：全国覆盖情况\n"
            "4. 附加服务：绿通、垫付等\n\n"
            "大部分客户其实更看重服务和安心感，而不只是价格。"
            "附上我的对比话术模板，希望对大家有帮助。"
        ),
        "category": "script",
        "tags": ["异议处理", "比价应对", "实战分享"],
        "author_phone": "13800138002",
        "views_count": 789,
        "likes_count": 234,
        "comments_count": 47,
        "favorites_count": 55,
        "is_pinned": False,
        "is_recommended": False,
        "created_at": datetime.now(timezone.utc) - timedelta(days=2),
    },
    {
        "id": uuid.UUID("10000001-0001-4000-8000-000000000006"),
        "title": "知识分享：重疾险等待期内出险怎么处理？",
        "content": (
            "最近有同事问到一个常见问题：重疾险等待期内出险怎么处理？\n\n"
            "## 等待期基本规则\n\n"
            "大多数重疾险等待期为90天或180天。等待期内出险的处理方式取决于具体产品和出险类型：\n\n"
            "### 意外事故\n\n"
            "意外事故导致的重疾一般不受等待期限制，可以正常理赔。\n\n"
            "### 非意外疾病\n\n"
            "- **等待期内确诊重疾**：通常退还已交保费，合同终止\n"
            "- **等待期内确诊轻症**：部分产品仅该轻症责任终止，其余保障继续有效\n\n"
            "## 注意事项\n\n"
            "1. 投保时务必向客户说明等待期条款\n"
            "2. 不同产品条款可能有差异，以合同为准\n"
            "3. 遇到具体案例建议先咨询理赔部门"
        ),
        "category": "knowledge",
        "tags": ["重疾险", "等待期", "理赔知识"],
        "author_phone": "13800138003",
        "views_count": 623,
        "likes_count": 145,
        "comments_count": 31,
        "favorites_count": 38,
        "is_pinned": False,
        "is_recommended": False,
        "created_at": datetime.now(timezone.utc) - timedelta(days=3),
    },
    {
        "id": uuid.UUID("10000001-0001-4000-8000-000000000007"),
        "title": "年金险适合哪些客户群体？如何精准定位？",
        "content": (
            "年金险的销售需要精准定位客户群体，分享我的实战经验。\n\n"
            "## 适合人群\n\n"
            "1. 有退休规划的中年客户（35-55岁）\n"
            "2. 子女教育金规划的家庭\n"
            "3. 有资产传承需求的高净值客户\n"
            "4. 追求稳健收益的保守型客户\n\n"
            "## 精准定位话术\n\n"
            "\"您平时有没有考虑过，退休后的生活品质怎么保障？\" "
            "用这个开场白可以有效筛选出有年金险需求的客户。"
        ),
        "category": "discussion",
        "tags": ["年金险", "客户定位", "销售策略"],
        "author_phone": "13800138001",
        "views_count": 432,
        "likes_count": 98,
        "comments_count": 22,
        "favorites_count": 18,
        "is_pinned": False,
        "is_recommended": False,
        "created_at": datetime.now(timezone.utc) - timedelta(days=5),
    },
    {
        "id": uuid.UUID("10000001-0001-4000-8000-000000000008"),
        "title": "优秀话术模板：首次拜访开场白",
        "content": (
            "分享我总结的5种高转化首次拜访开场白，适用于不同客户类型。\n\n"
            "## 1. 亲近型开场\n"
            "\"XX姐，上次您提到孩子刚上学，最近有没有考虑给孩子的未来做一个长远规划？\"\n\n"
            "## 2. 专业型开场\n"
            "\"XX先生，最近市场波动比较大，很多客户在重新评估家庭资产配置，不知道您有没有关注过？\"\n\n"
            "## 3. 关怀型开场\n"
            "\"XX姐，天凉了注意保暖。对了，上次您说想了解的健康保障方案，我整理好了，您看什么时候方便？\"\n\n"
            "## 4. 新闻型开场\n"
            "\"XX先生，您看到最近那个XX新闻了吗？其实这也提醒我们，风险保障真的很重要。\"\n\n"
            "## 5. 社交型开场\n"
            "\"XX姐，我这边有几位跟您情况类似的客户，他们的保障方案可能对您有参考价值。\""
        ),
        "category": "script",
        "tags": ["话术模板", "首次拜访", "开场白"],
        "author_phone": "13800138002",
        "views_count": 1567,
        "likes_count": 389,
        "comments_count": 56,
        "favorites_count": 112,
        "is_pinned": False,
        "is_recommended": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=1, hours=3),
    },
]

_DEMO_COMMENTS: dict[str, list[dict]] = {
    "10000001-0001-4000-8000-000000000001": [
        {
            "id": uuid.UUID("20000001-0001-4000-8000-000000000001"),
            "content": "非常实用的分享！我也经常用类似的方法，补充一点：在问第三个问题时可以结合具体产品来引导。",
            "author_phone": "13800138000",
            "likes_count": 12,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        {
            "id": uuid.UUID("20000001-0001-4000-8000-000000000002"),
            "content": "第三个问题的问法很巧妙，既不冒犯又能获取关键信息。学习了！",
            "author_phone": "13800138002",
            "likes_count": 8,
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=30),
        },
        {
            "id": uuid.UUID("20000001-0001-4000-8000-000000000003"),
            "content": "同意！我们团队内部培训也用了类似的方法论，效果确实好。补充一个：可以问\"您身边有没有朋友买过保险？体验怎么样？\"，这能帮你判断客户对保险的接受程度。",
            "author_phone": "13800138003",
            "parent_comment_id": uuid.UUID("20000001-0001-4000-8000-000000000001"),
            "likes_count": 5,
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=15),
        },
    ],
    "10000001-0001-4000-8000-000000000004": [
        {
            "id": uuid.UUID("20000001-0001-4000-8000-000000000004"),
            "content": "放轻松！紧张是正常的。建议你：1. 先打几个老客户电话练手 2. 面前放一张话术要点卡 3. 遇到不会的直接说\"这个问题比较专业，我确认后回复您\"",
            "author_phone": "13800138001",
            "likes_count": 15,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=4),
        },
        {
            "id": uuid.UUID("20000001-0001-4000-8000-000000000005"),
            "content": "我也是新人过来的，给你一个建议：不要追求一次电话就成交。把目标定为\"让客户记住你\"，第一次电话只要建立好感就成功了。",
            "author_phone": "13800138002",
            "likes_count": 9,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=3),
        },
    ],
    "10000001-0001-4000-8000-000000000005": [
        {
            "id": uuid.UUID("20000001-0001-4000-8000-000000000006"),
            "content": "四维对比法太棒了！我之前只会说\"我们公司服务好\"，太笼统了。用具体维度来对比更有说服力。",
            "author_phone": "13800138000",
            "likes_count": 7,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=12),
        },
        {
            "id": uuid.UUID("20000001-0001-4000-8000-000000000007"),
            "content": "补充一个维度：理赔纠纷率。可以向客户展示行业理赔数据，华安在这方面做得不错。",
            "author_phone": "13800138003",
            "parent_comment_id": uuid.UUID("20000001-0001-4000-8000-000000000006"),
            "likes_count": 4,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=10),
        },
    ],
}


def _make_author_brief(phone: str) -> AuthorBrief:
    info = _DEMO_USER_INFO.get(phone, {"name": "用户", "role": "agent", "org": "华安保险"})
    uid = _DEMO_USER_IDS.get(phone, uuid.uuid4())
    return AuthorBrief(
        id=uid,
        name=info["name"],
        role=info["role"],
        organization=info.get("org"),
    )


def _make_comment_author(phone: str) -> CommentAuthor:
    info = _DEMO_USER_INFO.get(phone, {"name": "用户"})
    uid = _DEMO_USER_IDS.get(phone, uuid.uuid4())
    return CommentAuthor(id=uid, name=info["name"])


def _post_to_list_item(post: dict, user_id: uuid.UUID | None = None) -> PostListItem:
    author = _make_author_brief(post["author_phone"])
    return PostListItem(
        id=post["id"],
        title=post["title"],
        author=author,
        category=post["category"],
        category_label=CATEGORY_LABELS.get(post["category"], post["category"]),
        summary=post.get("content", "")[:100] + "..." if post.get("content") else None,
        tags=post.get("tags", []),
        views_count=post.get("views_count", 0),
        likes_count=post.get("likes_count", 0),
        comments_count=post.get("comments_count", 0),
        is_pinned=post.get("is_pinned", False),
        is_recommended=post.get("is_recommended", False),
        created_at=post.get("created_at", datetime.now(timezone.utc)),
    )


def _post_to_detail(post: dict, user_id: uuid.UUID | None = None) -> PostDetail:
    item = _post_to_list_item(post, user_id)
    return PostDetail(
        **item.model_dump(),
        content=post.get("content", ""),
        ai_summary=post.get("ai_summary"),
        updated_at=post.get("updated_at", post.get("created_at")),
    )


class CommunityService:
    """社区服务 —— Demo 模式使用内存列表，生产模式使用数据库。"""

    def __init__(self, session: AsyncSession | None = None):
        self.session = session
        self._posts: dict[str, dict] = {str(p["id"]): p for p in _DEMO_POSTS}
        self._comments: dict[str, list[dict]] = dict(_DEMO_COMMENTS)
        self._likes: dict[str, set[str]] = {}  # post_id -> set[user_id]
        self._favorites: dict[str, set[str]] = {}  # post_id -> set[user_id]

    # ---- 帖子列表 ----

    async def list_posts(
        self,
        *,
        keyword: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[PostListItem], int]:
        """获取帖子列表，返回 (items, total)。"""
        if settings.DEMO_MODE:
            return await self._demo_list_posts(
                keyword=keyword, category=category, tags=tags, sort_by=sort_by,
                sort_order=sort_order, page=page, page_size=page_size, user_id=user_id,
            )
        # Production path
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        sort_map = {"created_at": "latest", "likes_count": "most_liked", "comments_count": "most_commented", "views_count": "latest"}
        db_sort = sort_map.get(sort_by, "latest")
        orm_posts, total = await repo.list_posts(page=page, page_size=page_size, category=category, search=keyword, sort_by=db_sort)
        items = [_post_to_list_item({"id": p.id, "title": p.title, "author_phone": "", "category": p.category or "", "created_at": p.created_at, "views_count": p.views_count or 0, "likes_count": p.likes_count or 0, "comments_count": p.comments_count or 0, "is_pinned": p.is_pinned or False, "is_recommended": False, "tags": []}, user_id) for p in orm_posts]
        return items, total

    async def _demo_list_posts(
        self,
        *,
        keyword: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[PostListItem], int]:
        """Demo: 获取帖子列表。"""
        posts = list(self._posts.values())

        # 筛选
        if keyword:
            kw = keyword.lower()
            posts = [p for p in posts if kw in p.get("title", "").lower() or kw in p.get("content", "").lower()]
        if category:
            posts = [p for p in posts if p.get("category") == category]
        if tags:
            posts = [p for p in posts if any(t in (p.get("tags") or []) for t in tags)]

        # 置顶的排最前
        pinned = [p for p in posts if p.get("is_pinned")]
        normal = [p for p in posts if not p.get("is_pinned")]

        def _sort_key(p: dict):
            if sort_by == "likes_count":
                return p.get("likes_count", 0)
            elif sort_by == "comments_count":
                return p.get("comments_count", 0)
            elif sort_by == "views_count":
                return p.get("views_count", 0)
            return p.get("created_at", datetime.min.replace(tzinfo=timezone.utc))

        reverse = sort_order == "desc"
        pinned.sort(key=_sort_key, reverse=reverse)
        normal.sort(key=_sort_key, reverse=reverse)
        posts = pinned + normal

        total = len(posts)
        start = (page - 1) * page_size
        end = start + page_size
        items = [_post_to_list_item(p, user_id) for p in posts[start:end]]
        return items, total

    # ---- 帖子详情 ----

    async def get_post(
        self, post_id: str, user_id: uuid.UUID | None = None
    ) -> PostDetail | None:
        """获取帖子详情（自动+1浏览量）。"""
        if settings.DEMO_MODE:
            return await self._demo_get_post(post_id, user_id)
        # Production path
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        try:
            pid = uuid.UUID(post_id)
        except ValueError:
            return None
        post = await repo.get_by_id(pid)
        if post is None or post.is_deleted:
            return None
        post.views_count = (post.views_count or 0) + 1
        await self.session.flush()  # type: ignore[union-attr]
        return _post_to_detail({"id": post.id, "title": post.title, "author_phone": "", "category": post.category or "", "content": post.content or "", "created_at": post.created_at, "updated_at": post.updated_at, "views_count": post.views_count, "likes_count": post.likes_count or 0, "comments_count": post.comments_count or 0, "is_pinned": post.is_pinned or False, "is_recommended": False, "tags": [], "ai_summary": post.ai_summary}, user_id)

    async def _demo_get_post(
        self, post_id: str, user_id: uuid.UUID | None = None
    ) -> PostDetail | None:
        """Demo: 获取帖子详情。"""
        post = self._posts.get(post_id)
        if post is None:
            return None
        # 增加浏览量
        post["views_count"] = post.get("views_count", 0) + 1
        return _post_to_detail(post, user_id)

    # ---- 创建帖子 ----

    async def create_post(
        self, data: PostCreate, author_id: uuid.UUID, author_phone: str
    ) -> dict:
        """创建帖子。"""
        if settings.DEMO_MODE:
            return await self._demo_create_post(data, author_id, author_phone)
        # Production path
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        from app.models.community import Post
        now = datetime.now(timezone.utc)
        post = Post(
            title=data.title.strip(),
            content=data.content.strip(),
            category=data.category,
            tags=data.tags[:5],
            author_id=author_id,
            status="published",
        )
        self.session.add(post)  # type: ignore[union-attr]
        await self.session.flush()  # type: ignore[union-attr]
        return {"id": str(post.id), "title": post.title, "status": "published", "created_at": now}

    async def _demo_create_post(
        self, data: PostCreate, author_id: uuid.UUID, author_phone: str
    ) -> dict:
        """Demo: 创建帖子。"""
        post_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        content = data.content.strip()
        summary = content[:100] + "..." if len(content) > 100 else content

        post = {
            "id": uuid.UUID(post_id),
            "title": data.title.strip(),
            "content": content,
            "summary": summary,
            "category": data.category,
            "tags": data.tags[:5],
            "author_phone": author_phone,
            "views_count": 0,
            "likes_count": 0,
            "comments_count": 0,
            "favorites_count": 0,
            "is_pinned": False,
            "is_recommended": False,
            "status": "published",
            "ai_summary": None,
            "created_at": now,
            "updated_at": now,
        }
        self._posts[post_id] = post
        self._comments.setdefault(post_id, [])
        return {"id": post_id, "title": post["title"], "status": "published", "created_at": now}

    # ---- 更新帖子 ----

    async def update_post(
        self, post_id: str, data: PostUpdate, user_id: uuid.UUID
    ) -> dict | None:
        """更新帖子。"""
        if settings.DEMO_MODE:
            return await self._demo_update_post(post_id, data, user_id)
        # Production path
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        try:
            pid = uuid.UUID(post_id)
        except ValueError:
            return None
        post = await repo.get_by_id(pid)
        if post is None or post.is_deleted:
            return None
        if data.title is not None:
            post.title = data.title.strip()
        if data.content is not None:
            post.content = data.content.strip()
        if data.category is not None:
            post.category = data.category
        if data.tags is not None:
            post.tags = data.tags[:5]
        post.updated_at = datetime.now(timezone.utc)
        await self.session.flush()  # type: ignore[union-attr]
        return {"id": post_id, "status": "published", "updated_at": post.updated_at}

    async def _demo_update_post(
        self, post_id: str, data: PostUpdate, user_id: uuid.UUID
    ) -> dict | None:
        """Demo: 更新帖子。"""
        post = self._posts.get(post_id)
        if post is None:
            return None

        if data.title is not None:
            post["title"] = data.title.strip()
        if data.content is not None:
            post["content"] = data.content.strip()
            post["summary"] = data.content[:100] + "..."
        if data.category is not None:
            post["category"] = data.category
        if data.tags is not None:
            post["tags"] = data.tags[:5]
        post["updated_at"] = datetime.now(timezone.utc)
        post["status"] = "published"
        return {"id": post_id, "status": "published", "updated_at": post["updated_at"]}

    # ---- 删除帖子 ----

    async def delete_post(self, post_id: str) -> bool:
        """删除帖子。"""
        if settings.DEMO_MODE:
            return await self._demo_delete_post(post_id)
        # Production path
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        try:
            pid = uuid.UUID(post_id)
        except ValueError:
            return False
        post = await repo.get_by_id(pid)
        if post is None:
            return False
        post.is_deleted = True
        await self.session.flush()  # type: ignore[union-attr]
        return True

    async def _demo_delete_post(self, post_id: str) -> bool:
        """Demo: 删除帖子。"""
        if post_id not in self._posts:
            return False
        del self._posts[post_id]
        self._comments.pop(post_id, None)
        self._likes.pop(post_id, None)
        self._favorites.pop(post_id, None)
        return True

    # ---- 点赞 ----

    async def toggle_like(
        self, post_id: str, user_id: uuid.UUID
    ) -> LikeToggleResponse | None:
        """切换点赞状态。"""
        if settings.DEMO_MODE:
            return await self._demo_toggle_like(post_id, user_id)
        # Production path
        try:
            pid = uuid.UUID(post_id)
        except ValueError:
            return None
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        like_repo = PostLikeRepository(self.session)  # type: ignore[arg-type]
        post = await repo.get_by_id(pid)
        if post is None or post.is_deleted:
            return None
        is_liked = await like_repo.toggle(user_id, pid)
        new_count = (post.likes_count or 0) + (1 if is_liked else -1)
        post.likes_count = max(0, new_count)
        await self.session.flush()  # type: ignore[union-attr]
        return LikeToggleResponse(is_liked=is_liked, likes_count=post.likes_count)

    async def _demo_toggle_like(
        self, post_id: str, user_id: uuid.UUID
    ) -> LikeToggleResponse | None:
        """Demo: 切换点赞状态。"""
        post = self._posts.get(post_id)
        if post is None:
            return None
        uid = str(user_id)
        liked = self._likes.setdefault(post_id, set())
        if uid in liked:
            liked.discard(uid)
            post["likes_count"] = max(0, post.get("likes_count", 0) - 1)
            return LikeToggleResponse(is_liked=False, likes_count=post["likes_count"])
        else:
            liked.add(uid)
            post["likes_count"] = post.get("likes_count", 0) + 1
            return LikeToggleResponse(is_liked=True, likes_count=post["likes_count"])

    # ---- 收藏 ----

    async def toggle_favorite(
        self, post_id: str, user_id: uuid.UUID
    ) -> FavoriteToggleResponse | None:
        """切换收藏状态。"""
        if settings.DEMO_MODE:
            return await self._demo_toggle_favorite(post_id, user_id)
        # Production path
        try:
            pid = uuid.UUID(post_id)
        except ValueError:
            return None
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        fav_repo = PostFavoriteRepository(self.session)  # type: ignore[arg-type]
        post = await repo.get_by_id(pid)
        if post is None or post.is_deleted:
            return None
        is_fav = await fav_repo.toggle(user_id, pid)
        new_count = (post.favorites_count or 0) + (1 if is_fav else -1)
        post.favorites_count = max(0, new_count)
        await self.session.flush()  # type: ignore[union-attr]
        return FavoriteToggleResponse(is_favorited=is_fav, favorites_count=post.favorites_count)

    async def _demo_toggle_favorite(
        self, post_id: str, user_id: uuid.UUID
    ) -> FavoriteToggleResponse | None:
        """Demo: 切换收藏状态。"""
        post = self._posts.get(post_id)
        if post is None:
            return None
        uid = str(user_id)
        favs = self._favorites.setdefault(post_id, set())
        if uid in favs:
            favs.discard(uid)
            post["favorites_count"] = max(0, post.get("favorites_count", 0) - 1)
            return FavoriteToggleResponse(is_favorited=False, favorites_count=post["favorites_count"])
        else:
            favs.add(uid)
            post["favorites_count"] = post.get("favorites_count", 0) + 1
            return FavoriteToggleResponse(is_favorited=True, favorites_count=post["favorites_count"])

    # ---- 评论 ----

    async def add_comment(
        self, post_id: str, data: CommentCreate, author_id: uuid.UUID, author_phone: str
    ) -> dict | None:
        """添加评论。"""
        if settings.DEMO_MODE:
            return await self._demo_add_comment(post_id, data, author_id, author_phone)
        # Production path
        try:
            pid = uuid.UUID(post_id)
        except ValueError:
            return None
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        comment_repo = PostCommentRepository(self.session)  # type: ignore[arg-type]
        post = await repo.get_by_id(pid)
        if post is None or post.is_deleted:
            return None
        from app.models.community import PostComment
        now = datetime.now(timezone.utc)
        comment = PostComment(
            post_id=pid,
            author_id=author_id,
            content=data.content.strip(),
            parent_comment_id=data.parent_comment_id,
        )
        self.session.add(comment)  # type: ignore[union-attr]
        post.comments_count = (post.comments_count or 0) + 1
        await self.session.flush()  # type: ignore[union-attr]
        return {
            "id": str(comment.id),
            "content": comment.content,
            "author": {"id": author_id, "name": ""},
            "parent_comment_id": str(data.parent_comment_id) if data.parent_comment_id else None,
            "created_at": now,
        }

    async def _demo_add_comment(
        self, post_id: str, data: CommentCreate, author_id: uuid.UUID, author_phone: str
    ) -> dict | None:
        """Demo: 添加评论。"""
        post = self._posts.get(post_id)
        if post is None:
            return None
        comment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        comment = {
            "id": uuid.UUID(comment_id),
            "content": data.content.strip(),
            "author_phone": author_phone,
            "parent_comment_id": str(data.parent_comment_id) if data.parent_comment_id else None,
            "likes_count": 0,
            "created_at": now,
        }
        comments = self._comments.setdefault(post_id, [])
        comments.insert(0, comment)  # 新评论在前
        post["comments_count"] = len(comments)
        return {
            "id": comment_id,
            "content": comment["content"],
            "author": _make_comment_author(author_phone),
            "parent_comment_id": comment["parent_comment_id"],
            "created_at": now,
        }

    async def list_comments(
        self, post_id: str, page: int = 1, page_size: int = 20, user_id: uuid.UUID | None = None
    ) -> tuple[list[CommentItem], int]:
        """获取帖子评论列表。"""
        if settings.DEMO_MODE:
            return await self._demo_list_comments(post_id, page, page_size, user_id)
        # Production path
        try:
            pid = uuid.UUID(post_id)
        except ValueError:
            return [], 0
        comment_repo = PostCommentRepository(self.session)  # type: ignore[arg-type]
        orm_comments, total = await comment_repo.list_by_post(pid, page=page, page_size=page_size)
        # Build comment tree
        top_comments = [c for c in orm_comments if not c.parent_comment_id]
        replies_map: dict[str, list] = {}
        for c in orm_comments:
            if c.parent_comment_id:
                replies_map.setdefault(str(c.parent_comment_id), []).append(c)
        items = []
        for c in top_comments:
            replies = replies_map.get(str(c.id), [])
            items.append(
                CommentItem(
                    id=c.id,
                    content=c.content,
                    author=CommentAuthor(id=c.author_id, name=""),
                    parent_comment_id=None,
                    likes_count=c.likes_count or 0,
                    replies=[
                        CommentItem(
                            id=r.id, content=r.content,
                            author=CommentAuthor(id=r.author_id, name=""),
                            parent_comment_id=str(r.parent_comment_id),
                            likes_count=r.likes_count or 0,
                            created_at=r.created_at,
                        )
                        for r in replies
                    ],
                    created_at=c.created_at,
                )
            )
        return items, total

    async def _demo_list_comments(
        self, post_id: str, page: int = 1, page_size: int = 20, user_id: uuid.UUID | None = None
    ) -> tuple[list[CommentItem], int]:
        """Demo: 获取帖子评论列表。"""
        raw_comments = self._comments.get(post_id, [])

        # 分离顶级评论和回复
        top_comments = [c for c in raw_comments if not c.get("parent_comment_id")]
        replies_map: dict[str, list[dict]] = {}
        for c in raw_comments:
            pid = c.get("parent_comment_id")
            if pid:
                replies_map.setdefault(pid, []).append(c)

        items = []
        for c in top_comments:
            replies = replies_map.get(str(c["id"]), [])
            items.append(
                CommentItem(
                    id=c["id"],
                    content=c["content"],
                    author=_make_comment_author(c["author_phone"]),
                    parent_comment_id=None,
                    likes_count=c.get("likes_count", 0),
                    replies=[
                        CommentItem(
                            id=r["id"],
                            content=r["content"],
                            author=_make_comment_author(r["author_phone"]),
                            parent_comment_id=r.get("parent_comment_id"),
                            likes_count=r.get("likes_count", 0),
                            created_at=r["created_at"],
                        )
                        for r in replies
                    ],
                    created_at=c["created_at"],
                )
            )

        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    # ---- 我的收藏 ----

    async def my_favorites(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[PostListItem], int]:
        """获取当前用户的收藏帖子列表。"""
        if settings.DEMO_MODE:
            return await self._demo_my_favorites(user_id, page, page_size)
        # Production path
        repo = PostRepository(self.session)  # type: ignore[arg-type]
        orm_posts, total = await repo.list_user_favorites(user_id, page=page, page_size=page_size)
        items = [_post_to_list_item({"id": p.id, "title": p.title, "author_phone": "", "category": p.category or "", "created_at": p.created_at, "views_count": p.views_count or 0, "likes_count": p.likes_count or 0, "comments_count": p.comments_count or 0, "is_pinned": False, "is_recommended": False, "tags": []}, user_id) for p in orm_posts]
        return items, total

    async def _demo_my_favorites(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[PostListItem], int]:
        """Demo: 获取当前用户的收藏帖子列表。"""
        uid = str(user_id)
        fav_post_ids = []
        for post_id, users in self._favorites.items():
            if uid in users:
                fav_post_ids.append(post_id)

        fav_posts = [self._posts[pid] for pid in fav_post_ids if pid in self._posts]
        # 按收藏时间倒序（简单处理）
        fav_posts.sort(key=lambda p: p.get("created_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)

        total = len(fav_posts)
        start = (page - 1) * page_size
        items = [_post_to_list_item(p, user_id) for p in fav_posts[start : start + page_size]]
        return items, total

    # ---- AI 摘要 SSE ----

    async def generate_ai_summary(
        self, post_id: str
    ) -> AsyncGenerator[str, None]:
        """生成 AI 摘要（SSE 流式）。"""
        if settings.DEMO_MODE:
            async for event in self._demo_generate_ai_summary(post_id):
                yield event
            return
        # Production path — simple event stream placeholder
        yield json.dumps({"event": "summary_start", "data": {"post_id": post_id}}, ensure_ascii=False)
        await asyncio.sleep(0.3)
        summary_text = "AI 摘要生成功能将在生产环境中接入 AI 网关。"
        for i, char in enumerate(summary_text):
            yield json.dumps(
                {"event": "token", "data": {"content": char, "index": i}},
                ensure_ascii=False,
            )
            await asyncio.sleep(0.02)
        yield json.dumps(
            {"event": "summary_complete", "data": {"summary": summary_text}},
            ensure_ascii=False,
        )

    async def _demo_generate_ai_summary(
        self, post_id: str
    ) -> AsyncGenerator[str, None]:
        """Demo: 生成 AI 摘要（SSE 流式）。"""
        post = self._posts.get(post_id)
        if post is None:
            yield json.dumps({"event": "error", "data": {"message": "帖子不存在"}}, ensure_ascii=False)
            return

        content = post.get("content", "")
        title = post.get("title", "")

        # Demo模式：模拟AI摘要生成
        yield json.dumps({"event": "summary_start", "data": {"post_id": post_id}}, ensure_ascii=False)
        await asyncio.sleep(0.3)

        # 基于内容的模拟摘要
        if len(content) > 200:
            sentences = content.replace("\n", " ").split("。")
            key_points = [s.strip() for s in sentences if len(s.strip()) > 15][:3]
            summary_text = "。".join(key_points[:3]) + "。"
            if len(summary_text) < 20:
                summary_text = f"本文分享了关于{title}的实战经验和具体方法，帮助保险代理人提升业务能力。"
        else:
            summary_text = f"本文讨论了关于{title}的话题，社区成员积极参与讨论。"

        # 逐字输出
        for i, char in enumerate(summary_text):
            yield json.dumps(
                {"event": "token", "data": {"content": char, "index": i}},
                ensure_ascii=False,
            )
            await asyncio.sleep(0.02)

        # 完成
        post["ai_summary"] = summary_text
        yield json.dumps(
            {"event": "summary_complete", "data": {"summary": summary_text}},
            ensure_ascii=False,
        )

    # ---- 判断用户是否已点赞/收藏 ----

    def _is_liked(self, post_id: str, user_id: uuid.UUID) -> bool:
        return str(user_id) in self._likes.get(post_id, set())

    def _is_favorited(self, post_id: str, user_id: uuid.UUID) -> bool:
        return str(user_id) in self._favorites.get(post_id, set())


# ---- 全局单例 ----

_community_service: CommunityService | None = None


def get_community_service() -> CommunityService:
    """获取社区服务单例。"""
    global _community_service
    if _community_service is None:
        _community_service = CommunityService(session=None)
    return _community_service
