"""RAG 安全模块 —— 拒答机制、置信度门控、Prompt Injection 防护。"""
import re
import base64
from dataclasses import dataclass, field
from enum import Enum

from app.rag.retriever import SearchResult


# ==================================================================
# 数据类
# ==================================================================


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class SeverityLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# 初始化顺序映射
_SEVERITY_ORDER = {
    SeverityLevel.NONE: 0,
    SeverityLevel.LOW: 1,
    SeverityLevel.MEDIUM: 2,
    SeverityLevel.HIGH: 3,
}


@dataclass
class ConfidenceResult:
    """置信度评估结果。"""
    level: ConfidenceLevel
    top_score: float
    result_count: int
    explanation: str


@dataclass
class InjectionResult:
    """Prompt Injection 检测结果。"""
    is_malicious: bool
    severity: SeverityLevel
    attack_types: list[str] = field(default_factory=list)
    sanitized_text: str = ""


# ==================================================================
# 1. 拒答判断
# ==================================================================

def should_refuse_answer(
    search_results: list[SearchResult],
    threshold: float = 0.3,
) -> tuple[bool, float, int]:
    """判断是否应该拒答。

    Args:
        search_results: 检索结果列表
        threshold: 最低相关性阈值，默认 0.3

    Returns:
        (should_refuse, top_score, result_count)
    """
    result_count = len(search_results)

    # 空结果 → 拒答
    if result_count == 0:
        return (True, 0.0, 0)

    # 最高分
    top_score = max(r.score for r in search_results)

    # 最高分低于阈值 → 拒答
    if top_score < threshold:
        return (True, top_score, result_count)

    return (False, top_score, result_count)


# ==================================================================
# 2. 置信度门控
# ==================================================================

_CONFIDENCE_EXPLANATIONS = {
    ConfidenceLevel.HIGH: "检索到高质量、数量充足的参考内容，回答可信度高。",
    ConfidenceLevel.MEDIUM: "检索到一定数量的参考内容，回答可信度中等。",
    ConfidenceLevel.LOW: "检索结果有限，回答仅供参考，建议结合人工确认。",
    ConfidenceLevel.NONE: "未检索到足够相关的参考内容，无法可靠回答。",
}


def assess_confidence(
    search_results: list[SearchResult],
) -> ConfidenceResult:
    """评估 RAG 检索结果的置信度等级。

    等级规则:
    - HIGH:  top_score >= 0.7 且 results >= 3
    - MEDIUM: top_score >= 0.4 且 results >= 2
    - LOW:   top_score >= 0.3
    - NONE:  低于 0.3

    Returns:
        ConfidenceResult(level, top_score, result_count, explanation)
    """
    result_count = len(search_results)

    if result_count == 0:
        return ConfidenceResult(
            level=ConfidenceLevel.NONE,
            top_score=0.0,
            result_count=0,
            explanation=_CONFIDENCE_EXPLANATIONS[ConfidenceLevel.NONE],
        )

    top_score = max(r.score for r in search_results)

    if top_score >= 0.7 and result_count >= 3:
        level = ConfidenceLevel.HIGH
    elif top_score >= 0.4 and result_count >= 2:
        level = ConfidenceLevel.MEDIUM
    elif top_score >= 0.3:
        level = ConfidenceLevel.LOW
    else:
        level = ConfidenceLevel.NONE

    return ConfidenceResult(
        level=level,
        top_score=top_score,
        result_count=result_count,
        explanation=_CONFIDENCE_EXPLANATIONS[level],
    )


# ==================================================================
# 3. Prompt Injection 检测
# ==================================================================

# --- 攻击规则定义 ---

_INJECTION_RULES: list[tuple[str, re.Pattern, SeverityLevel]] = [
    # 1. 角色劫持
    ("role_hijack", re.compile(
        r"(你是现在|忽略之前|假装你是|你现在是|你不再是|act as|you are now|pretend you|"
        r"ignore previous|forget everything|disregard all|roleplay as)",
        re.IGNORECASE,
    ), SeverityLevel.HIGH),

    # 2. 指令泄露
    ("instruction_leak", re.compile(
        r"(显示.*?系统提示|输出.*?prompt|打印.*?你的|show.*?system.*?prompt|repeat.*?your.*?instructions|"
        r"reveal.*?your.*?rules|print.*?your.*?instructions|输出.*?你的.*?指令|展示.*?你的.*?设定|"
        r"what are your instructions|tell me your prompt)",
        re.IGNORECASE,
    ), SeverityLevel.MEDIUM),

    # 3. 分隔符攻击
    ("delimiter_attack", re.compile(
        r"(---\s*以上内容忽略|<\|end\|>|===end===|above instructions|"
        r"以上内容全部忽略|ignore everything above|<\|im_end\|>|"
        r"以上指令全部忽略|end of prompt)",
        re.IGNORECASE,
    ), SeverityLevel.HIGH),

    # 4. JSON 注入
    ("json_injection", re.compile(
        r'(\{[\s]*"(system|role|instruction|prompt)"\s*:\s*")',
        re.IGNORECASE,
    ), SeverityLevel.MEDIUM),
]


# 5. 编码绕过检测（非正则，独立函数）


def _detect_encoding_bypass(text: str) -> tuple[bool, SeverityLevel]:
    """检测 Base64 长字符串和大量连续特殊字符。"""
    # Base64 长字符串检测（>= 40 字符的 Base64 片段）
    base64_pattern = re.compile(r'[A-Za-z0-9+/=]{40,}')
    if base64_pattern.search(text):
        return (True, SeverityLevel.MEDIUM)

    # 大量连续特殊字符（>= 10 个连续非字母数字非空格字符）
    special_pattern = re.compile(r'[^\w\s\u4e00-\u9fff]{10,}')
    if special_pattern.search(text):
        return (True, SeverityLevel.LOW)

    return (False, SeverityLevel.NONE)


def detect_prompt_injection(text: str) -> InjectionResult:
    """检测用户输入中的 Prompt Injection 攻击。

    多规则检测：正则 + 关键词 + 模式匹配。

    Returns:
        InjectionResult(is_malicious, severity, attack_types, sanitized_text)
    """
    attack_types: list[str] = []
    max_severity = SeverityLevel.NONE
    sanitized = text

    # 规则 1-4: 正则匹配
    for attack_name, pattern, severity in _INJECTION_RULES:
        if pattern.search(text):
            attack_types.append(attack_name)
            if _SEVERITY_ORDER[severity] > _SEVERITY_ORDER[max_severity]:
                max_severity = severity
            # 移除匹配到的恶意内容
            sanitized = pattern.sub("[已过滤]", sanitized)

    # 规则 5: 编码绕过
    is_bypass, bypass_severity = _detect_encoding_bypass(text)
    if is_bypass:
        attack_types.append("encoding_bypass")
        if _SEVERITY_ORDER[bypass_severity] > _SEVERITY_ORDER[max_severity]:
            max_severity = bypass_severity
        # 清理 Base64 长串
        sanitized = re.sub(r'[A-Za-z0-9+/=]{40,}', '[已过滤]', sanitized)
        # 清理连续特殊字符
        sanitized = re.sub(r'[^\w\s\u4e00-\u9fff]{10,}', '[已过滤]', sanitized)

    is_malicious = len(attack_types) > 0

    return InjectionResult(
        is_malicious=is_malicious,
        severity=max_severity,
        attack_types=attack_types,
        sanitized_text=sanitized,
    )


# ==================================================================
# 4. 输入消毒
# ==================================================================


def sanitize_user_input(raw_input: str) -> tuple[str, InjectionResult]:
    """清洗用户输入。

    处理步骤:
    1. 去除多余空白/换行（保留最多 2 个连续换行）
    2. 限制输入长度（最大 2000 字符，超出截断并加前缀）
    3. 移除控制字符（保留正常换行和制表符）
    4. 调用 detect_prompt_injection 进行安全检查

    Returns:
        (sanitized_text, safety_check_result)
    """
    text = raw_input

    # Step 1: 移除控制字符（保留 \n 和 \t）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Step 2: 去除多余空白/换行（保留最多 2 个连续换行）
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)  # 多个空格/Tab → 单空格
    text = text.strip()

    # Step 3: 限制输入长度
    MAX_INPUT_LENGTH = 2000
    if len(text) > MAX_INPUT_LENGTH:
        text = "[输入已截断]" + text[:MAX_INPUT_LENGTH]

    # Step 4: Prompt Injection 安全检查
    safety_check = detect_prompt_injection(text)

    return (text, safety_check)
