"""话术生成服务 —— AI多风格话术生成 + 合规检查。"""
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from structlog import get_logger

from app.ai.gateway import get_ai_gateway
from app.core.config import settings
from app.models.user import User
from app.services.compliance_service import check_compliance, build_script_prompt, STYLE_PROMPTS

logger = get_logger()

# ---- Demo 话术数据 ----

_DEMO_SCRIPTS: list[dict] = [
    {
        "id": "demo-scr-001",
        "title": "陈先生百万医疗险-亲和型",
        "customer_context": {"name": "陈志明", "age": 45, "objection": "太贵了", "stage": "proposal", "product_type": "医疗险"},
        "style": "affinity",
        "content": "陈先生，我特别理解您的想法。说实话，我自己当年也是这么想的，觉得每个月花几百块买个\"万一\"，是不是有点多余？后来我身边一个朋友，平时身体挺好的，突然查出来需要做个手术，光住院费就花了十几万。那时候他才真正体会到，几百块一年的百万医疗险，关键时刻真能救命。您想想，咱们一天也就一块多钱，少喝一杯奶茶的事。万一真有什么情况，最高能报600万，连进口药、靶向药都能报。这不是花钱，这是给家人一份安心。",
        "product_type": "医疗险",
        "compliance_status": "green",
        "compliance_issues": None,
        "status": "published",
        "favorited_count": 23,
        "usage_count": 156,
        "created_at": "2025-01-10T00:00:00Z",
        "updated_at": "2025-01-15T00:00:00Z",
    },
    {
        "id": "demo-scr-002",
        "title": "陈先生百万医疗险-专业型",
        "customer_context": {"name": "陈志明", "age": 45, "objection": "太贵了", "stage": "proposal", "product_type": "医疗险"},
        "style": "professional",
        "content": "陈先生，让我们从专业角度来分析一下百万医疗险的性价比。根据银保监会数据，我国45岁以上人群年均住院率为12.3%，平均住院费用约2.5万元。华安百万医疗险年保费仅需680元（45岁有社保），保障额度高达600万。从风险对冲角度看，保费仅占年收入0.5%左右，但能覆盖99%以上的大额医疗支出风险。产品条款明确：一般医疗200万+重疾医疗400万，涵盖住院、特殊门诊、门诊手术、质子重离子治疗。1万元免赔额后100%报销（经社保），未经社保报销80%。建议您对比一下其他同类产品的免赔额和报销比例，华安的条款在同业中具有明显优势。",
        "product_type": "医疗险",
        "compliance_status": "green",
        "compliance_issues": None,
        "status": "published",
        "favorited_count": 18,
        "usage_count": 98,
        "created_at": "2025-01-10T00:00:00Z",
        "updated_at": "2025-01-15T00:00:00Z",
    },
    {
        "id": "demo-scr-003",
        "title": "王女士重疾险-亲和型",
        "customer_context": {"name": "王丽华", "age": 38, "objection": "我有社保了", "stage": "initial_contact", "product_type": "重疾险"},
        "style": "affinity",
        "content": "王姐，您有社保的意识就比很多人强了！不过社保确实只是基础保障，就像下雨天有一把伞，但暴雨来了还是会被淋湿。我给您讲个真实案例：上个月有位客户张女士，和您差不多年龄，也是觉得有社保就够了。结果体检查出了甲状腺结节，后来发展需要手术，社保报销了一部分，但后续的康复费、营养费、还有半年不能工作的收入损失，社保都管不了。如果有一份重疾险，确诊就赔付50万，这笔钱怎么用完全由您自己支配。您说，是不是多一份保障更踏实？",
        "product_type": "重疾险",
        "compliance_status": "green",
        "compliance_issues": None,
        "status": "published",
        "favorited_count": 31,
        "usage_count": 203,
        "created_at": "2025-01-11T00:00:00Z",
        "updated_at": "2025-01-16T00:00:00Z",
    },
    {
        "id": "demo-scr-004",
        "title": "李总意外险-数据驱动型",
        "customer_context": {"name": "李伟强", "age": 52, "customer_type": "企业主", "objection": "不差钱不需要", "stage": "initial_contact", "product_type": "意外险"},
        "style": "data_driven",
        "content": "李总，理解您的想法。但意外险的价值不在于\"赔多少钱\"，而在于风险转移的效率。来看一组数据：根据国家统计局，45-55岁人群意外事故发生率为2.7‰，平均治疗费用8.3万元。华安至尊版综合意外险，年保费568元，意外身故/伤残保额200万+猝死100万+意外医疗10万+住院津贴200元/天。投入产出比超过1:3500。另外，意外险是唯一不需要健康告知的险种，不限职业1-4类，投保次日即生效。对于您这样的企业主，我们更建议搭配交通意外险（航空500万+高铁200万），年保费仅需88元。两项合计656元/年，为您构建覆盖全天候、全场景的意外防护网。",
        "product_type": "意外险",
        "compliance_status": "green",
        "compliance_issues": None,
        "status": "published",
        "favorited_count": 15,
        "usage_count": 67,
        "created_at": "2025-01-12T00:00:00Z",
        "updated_at": "2025-01-16T00:00:00Z",
    },
    {
        "id": "demo-scr-005",
        "title": "赵女士年金险-简洁型",
        "customer_context": {"name": "赵小芳", "age": 30, "objection": "考虑一下", "stage": "needs_analysis", "product_type": "年金险"},
        "style": "concise",
        "content": "赵女士，年金险的核心价值就一句话：年轻时存钱，退休后领钱，写进合同有保障。年交3万交10年，60岁起每年领4.2万，活多久领多久。保证领取20年。现在开始规划，比等到40岁再想，能多攒近一半的养老金。我今天带了一份方案，我们花10分钟看看具体数字，您再决定也不迟。",
        "product_type": "年金险",
        "compliance_status": "green",
        "compliance_issues": None,
        "status": "published",
        "favorited_count": 12,
        "usage_count": 89,
        "created_at": "2025-01-13T00:00:00Z",
        "updated_at": "2025-01-17T00:00:00Z",
    },
    {
        "id": "demo-scr-006",
        "title": "刘先生寿险-专业型",
        "customer_context": {"name": "刘建国", "age": 55, "objection": "身体挺好的不需要", "stage": "proposal", "product_type": "寿险"},
        "style": "professional",
        "content": "刘先生，我理解您目前身体状态良好。但寿险的本质不是保障自己，而是保障家人的生活质量。您今年55岁，正是家庭责任最重的时期——可能有房贷、有子女教育支出、有父母赡养。根据LIMRA数据，中国家庭寿险覆盖率仅约20%，意味着80%的家庭在主要经济支柱意外丧失后面临严重的财务困境。华安定期寿险，55岁男性保至70岁，100万保额年保费仅2,200元。建议寿险保额=房贷余额+子女教育费用+5年家庭开支。这是对家人最负责任的保障安排。",
        "product_type": "寿险",
        "compliance_status": "yellow",
        "compliance_issues": {"score": 80, "issues": [{"rule": "绝对化表达", "matched_text": "最负责任", "suggestion": "可改为'重要的保障安排'"}]},
        "status": "published",
        "favorited_count": 9,
        "usage_count": 45,
        "created_at": "2025-01-14T00:00:00Z",
        "updated_at": "2025-01-17T00:00:00Z",
    },
    {
        "id": "demo-scr-007",
        "title": "黄阿姨车险-亲和型",
        "customer_context": {"name": "黄秀英", "age": 48, "objection": "网上更便宜", "stage": "negotiation", "product_type": "车险"},
        "style": "affinity",
        "content": "黄阿姨，您说得对，网上确实有些报价看着便宜。但车险和别的商品不一样，关键是出事了能不能快速理赔、服务好不好。我们华安有一个客户，也是在网上买的便宜车险，出了事故后理赔特别折腾，折腾了快一个月才拿到钱。后来换到华安，小事故1小时就能快赔，还有免费道路救援、上门收资料。阿姨您想想，一年保费差个一两百，但关键时刻省的麻烦可不止这些。而且您连续投保华安，NCD折扣最多能到7折，长期算下来其实更划算。",
        "product_type": "车险",
        "compliance_status": "green",
        "compliance_issues": None,
        "status": "published",
        "favorited_count": 7,
        "usage_count": 38,
        "created_at": "2025-01-15T00:00:00Z",
        "updated_at": "2025-01-18T00:00:00Z",
    },
    # --- 合规问题示例 ---
    {
        "id": "demo-scr-008",
        "title": "张先生医疗险-合规违规示例",
        "customer_context": {"name": "张美玲", "age": 28, "objection": "有必要买吗", "stage": "initial_contact", "product_type": "医疗险"},
        "style": "professional",
        "content": "张先生，我们的百万医疗险保证您100%赔付，什么病都能报，肯定能通过核保，不用担心。不买就太亏了，最后机会，今天就下单吧！",
        "product_type": "医疗险",
        "compliance_status": "red",
        "compliance_issues": {"score": 40, "issues": [
            {"rule": "不当核保结论", "matched_text": "肯定能通过核保", "suggestion": "核保结论需由核保部门审核"},
            {"rule": "不当理赔承诺", "matched_text": "保证您100%赔付", "suggestion": "具体以合同条款为准"},
            {"rule": "夸大保障", "matched_text": "什么病都能报", "suggestion": "需明确保障范围"},
            {"rule": "诱导销售", "matched_text": "不买就太亏了，最后机会", "suggestion": "避免施压式销售"},
        ]},
        "status": "draft",
        "favorited_count": 0,
        "usage_count": 0,
        "created_at": "2025-01-18T00:00:00Z",
        "updated_at": "2025-01-18T00:00:00Z",
    },
]

_demo_initialized = False


def _ensure_demo_scripts():
    global _demo_initialized
    _demo_initialized = True


class ScriptService:
    """话术服务。"""

    def __init__(self, db=None):
        self.db = db
        self.gateway = get_ai_gateway()

    def get_scripts(self, filters: dict | None = None) -> list[dict]:
        """获取话术列表。"""
        _ensure_demo_scripts()
        scripts = list(_DEMO_SCRIPTS)
        if filters:
            if filters.get("style"):
                scripts = [s for s in scripts if s["style"] == filters["style"]]
            if filters.get("product_type"):
                scripts = [s for s in scripts if s.get("product_type") == filters["product_type"]]
            if filters.get("compliance_status"):
                scripts = [s for s in scripts if s["compliance_status"] == filters["compliance_status"]]
            if filters.get("status"):
                scripts = [s for s in scripts if s["status"] == filters["status"]]
            if filters.get("search"):
                q = filters["search"].lower()
                scripts = [s for s in scripts if q in s["title"].lower() or q in (s.get("content") or "").lower()]
        return scripts

    def get_script(self, script_id: str) -> dict | None:
        """获取话术详情。"""
        _ensure_demo_scripts()
        return next((s for s in _DEMO_SCRIPTS if s["id"] == script_id), None)

    def create_script(self, data: dict) -> dict:
        """创建话术。"""
        _ensure_demo_scripts()
        script = {
            "id": f"demo-scr-{uuid.uuid4().hex[:8]}",
            "title": data["title"],
            "customer_context": data.get("customer_context"),
            "style": data.get("style", "professional"),
            "content": data.get("content"),
            "product_type": data.get("product_type"),
            "compliance_status": data.get("compliance_status", "green"),
            "compliance_issues": None,
            "status": data.get("status", "draft"),
            "favorited_count": 0,
            "usage_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        # 合规检查
        if script["content"]:
            script["compliance_status"] = "green"
            script["compliance_issues"] = check_compliance(script["content"])
        _DEMO_SCRIPTS.append(script)
        return script

    def update_script(self, script_id: str, data: dict) -> dict | None:
        """更新话术。"""
        script = self.get_script(script_id)
        if script is None:
            return None
        for key, val in data.items():
            if key in script and key != "id":
                script[key] = val
        # 重新合规检查
        if "content" in data and script["content"]:
            result = check_compliance(script["content"])
            script["compliance_status"] = result["status"]
            script["compliance_issues"] = result
        script["updated_at"] = datetime.now(timezone.utc).isoformat()
        return script

    def delete_script(self, script_id: str) -> bool:
        """删除话术。"""
        global _DEMO_SCRIPTS
        original_len = len(_DEMO_SCRIPTS)
        _DEMO_SCRIPTS = [s for s in _DEMO_SCRIPTS if s["id"] != script_id]
        return len(_DEMO_SCRIPTS) < original_len

    def toggle_favorite(self, script_id: str) -> dict | None:
        """切换收藏。"""
        script = self.get_script(script_id)
        if script is None:
            return None
        script["favorited_count"] = script.get("favorited_count", 0) + 1
        return script

    async def generate_scripts(
        self,
        customer_context: dict,
        style: str | None = None,
        product_type: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """AI生成话术（SSE流式）。

        如果指定style则只生成一种，否则同时生成4种风格。
        """
        styles = [style] if style else ["affinity", "professional", "data_driven", "concise"]
        request_id = str(uuid.uuid4())

        yield _sse_event("generation_start", {
            "request_id": request_id,
            "styles": styles,
        })

        for s in styles:
            style_name = {
                "affinity": "亲和型",
                "professional": "专业型",
                "data_driven": "数据驱动型",
                "concise": "简洁型",
            }.get(s, s)

            yield _sse_event("style_start", {
                "style": s,
                "style_name": style_name,
            })

            prompt = build_script_prompt(s, customer_context)
            messages = [{"role": "system", "content": prompt}]

            full_content = ""
            try:
                stream = await self.gateway.chat(messages=messages, stream=True)
                async for token in stream:
                    full_content += token
                    yield _sse_event("token", {"style": s, "content": token})
            except Exception as e:
                logger.error("script_generation_error", style=s, error=str(e))
                full_content = "话术生成失败，请稍后重试。"
                yield _sse_event("token", {"style": s, "content": full_content})

            # 合规检查
            compliance = check_compliance(full_content)
            yield _sse_event("style_complete", {
                "style": s,
                "style_name": style_name,
                "content": full_content,
                "compliance": compliance,
            })

            # 保存到demo
            self.create_script({
                "title": f"AI生成-{style_name}",
                "customer_context": customer_context,
                "style": s,
                "content": full_content,
                "product_type": product_type,
                "compliance_status": compliance["status"],
                "compliance_issues": compliance,
                "status": "draft",
            })

        yield _sse_event("generation_complete", {
            "request_id": request_id,
            "total_styles": len(styles),
        })


def _sse_event(event_type: str, data: dict) -> str:
    return json.dumps({"event": event_type, "data": data}, ensure_ascii=False)
