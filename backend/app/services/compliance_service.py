"""合规检查服务 —— 规则引擎检测话术风险。"""
import re
from dataclasses import dataclass, field

from structlog import get_logger

logger = get_logger()


@dataclass
class _ComplianceRule:
    """合规规则。"""
    name: str
    description: str
    patterns: list[str]
    severity: str  # YELLOW or RED
    suggestion: str


# ---- 合规规则库 ----

COMPLIANCE_RULES: list[_ComplianceRule] = [
    _ComplianceRule(
        name="收益承诺",
        description="承诺确定收益",
        patterns=[
            r"保证.*收益", r"稳赚", r"肯定.*赚", r"百分之.*收益",
            r"收益.*保证", r"零风险.*收益", r"保本.*保息",
        ],
        severity="RED",
        suggestion="修改为「具体收益请以合同条款为准，过往业绩不代表未来表现」。",
    ),
    _ComplianceRule(
        name="绝对化表达",
        description="使用绝对化用词",
        patterns=[
            r"最好", r"唯一", r"100[%％].*赔付", r"绝对",
            r"一定.*能", r"完美", r"无.*风险",
        ],
        severity="YELLOW",
        suggestion="修改为相对表述，如「领先」「优质」等非绝对化用语。",
    ),
    _ComplianceRule(
        name="虚假比较",
        description="不当对比竞品",
        patterns=[
            r"比.*好多了", r"碾压", r"吊打", r"秒杀",
            r"最差.*是", r"不如.*我们",
        ],
        severity="YELLOW",
        suggestion="建议基于事实进行客观对比，避免贬低竞品。",
    ),
    _ComplianceRule(
        name="夸大保障",
        description="夸大保障范围",
        patterns=[
            r"什么.*都能报", r"无限.*报销", r"全部.*报销",
            r"不管.*什么病.*都赔", r"全部.*保障",
        ],
        severity="RED",
        suggestion="明确保障范围，建议查看具体条款细则。",
    ),
    _ComplianceRule(
        name="不当核保结论",
        description="给出核保结论",
        patterns=[
            r"肯定.*能.*过", r"不用担心.*核保", r"一定能.*投保",
            r"核保.*没问题", r"健康.*肯定.*通过",
        ],
        severity="RED",
        suggestion="核保结论需由公司核保部门审核，代理人不得给出确定性结论。",
    ),
    _ComplianceRule(
        name="不当理赔承诺",
        description="承诺理赔结果",
        patterns=[
            r"一定.*赔", r"秒赔", r"100.*%.*赔付",
            r"随便.*就能.*赔", r"马上.*到账",
        ],
        severity="RED",
        suggestion="修改为「具体理赔以保险合同及实际审核结果为准」。",
    ),
    _ComplianceRule(
        name="诱导销售",
        description="施压促单",
        patterns=[
            r"不买.*就.*没了", r"最后.*机会", r"仅限.*今天",
            r"再不买.*就.*晚了", r"错过.*后悔",
        ],
        severity="YELLOW",
        suggestion="避免施压式销售，建议以客户需求为导向进行沟通。",
    ),
    _ComplianceRule(
        name="敏感医疗结论",
        description="对健康状况下结论",
        patterns=[
            r"没事", r"不影响.*投保", r"小问题.*不算",
            r"不用.*告诉.*公司", r"瞒.*过去",
        ],
        severity="RED",
        suggestion="健康告知须如实填写，不得引导客户隐瞒健康状况。",
    ),
]


def check_compliance(text: str) -> dict:
    """对文本进行合规检查。

    Returns:
        {"status": "GREEN"/"YELLOW"/"RED", "score": 0-100, "issues": [...]}
    """
    issues: list[dict] = []
    worst_severity = "GREEN"

    for rule in COMPLIANCE_RULES:
        for pattern in rule.patterns:
            matches = re.findall(pattern, text)
            if matches:
                matched_text = matches[0]
                # 提取更完整的上下文
                for m in re.finditer(pattern, text):
                    start = max(0, m.start() - 10)
                    end = min(len(text), m.end() + 10)
                    matched_text = text[start:end]

                issues.append({
                    "rule": rule.name,
                    "matched_text": matched_text,
                    "suggestion": rule.suggestion,
                })
                if rule.severity == "RED":
                    worst_severity = "RED"
                elif rule.severity == "YELLOW" and worst_severity != "RED":
                    worst_severity = "YELLOW"
                break  # 每条规则只报一次

    # 计算分数
    score = 100
    for issue in issues:
        # 从规则名映射扣分
        if any(r.name == issue["rule"] and r.severity == "RED" for r in COMPLIANCE_RULES):
            score -= 20
        else:
            score -= 10
    score = max(0, score)

    # 无问题则检查关键词数量微调
    if worst_severity == "GREEN" and len(text) > 200:
        # 长文本有更多检查空间，微调分数
        score = min(100, score)

    result = {
        "status": worst_severity,
        "score": score,
        "issues": issues,
    }

    logger.info(
        "compliance_check_result",
        status=worst_severity,
        score=score,
        issues_count=len(issues),
    )

    return result


# ---- 话术生成提示词模板 ----

STYLE_PROMPTS: dict[str, str] = {
    "affinity": """你是华安保险的资深销售顾问，以亲和温暖的方式进行沟通。
风格要求：
- 像朋友一样聊天，语气温和亲切
- 多用故事和案例来建立共鸣
- 先理解客户担忧，再提出解决方案
- 避免过于正式的专业术语
- 适当表达关心，体现人情味""",

    "professional": """你是华安保险的资深产品顾问，以专业权威的方式进行沟通。
风格要求：
- 语言专业、逻辑清晰
- 引用产品条款和具体数据
- 逐步展开保障权益和理赔流程
- 展示专业素养，赢得客户信任
- 恰当使用行业术语但做通俗解释""",

    "data_driven": """你是华安保险的理财规划师，以数据驱动的方式进行沟通。
风格要求：
- 用具体数字说话，对比不同方案
- 引入概率、统计、行业数据
- 制作ROI对比和成本分析
- 适合理性分析型客户
- 让数据自己说话，不做空洞承诺""",

    "concise": """你是华安保险的高级销售，以简洁高效的方式进行沟通。
风格要求：
- 开门见山，直奔主题
- 每段不超过2-3句话
- 突出核心利益点
- 适合时间紧张的客户
- 最后一句必须是明确的行动号召""",
}


def build_script_prompt(style: str, customer_context: dict, product_info: str = "") -> str:
    """构建话术生成的系统提示词。"""
    style_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["professional"])

    ctx_parts = []
    if customer_context.get("name"):
        ctx_parts.append(f"客户姓名：{customer_context['name']}")
    if customer_context.get("age"):
        ctx_parts.append(f"年龄：{customer_context['age']}岁")
    if customer_context.get("customer_type"):
        ctx_parts.append(f"客户类型：{customer_context['customer_type']}")
    if customer_context.get("stage"):
        ctx_parts.append(f"销售阶段：{customer_context['stage']}")
    if customer_context.get("objection"):
        ctx_parts.append(f"当前异议：{customer_context['objection']}")
    if customer_context.get("product_type"):
        ctx_parts.append(f"关注产品：{customer_context['product_type']}")

    context_str = "\n".join(ctx_parts) if ctx_parts else "通用客户"

    prompt = f"""{style_prompt}

当前沟通对象：
{context_str}
"""

    if product_info:
        prompt += f"\n参考产品信息：\n{product_info}\n"

    prompt += """
要求：
1. 话术长度300-500字
2. 必须符合合规要求，不得包含收益承诺、绝对化表述、夸大保障等
3. 最后要自然引导到下一步行动（如预约面谈、提供方案等）
4. 使用口语化但专业的中文
5. 不要使用 [Demo/演示] 等标记"""

    return prompt
