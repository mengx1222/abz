import asyncio
import hashlib
import random
import time
import uuid
from typing import AsyncIterator

from structlog import get_logger

from app.ai.protocol import AIResponse, EmbedResponse, RerankResult

logger = get_logger()

# 关键词 -> 预设回复映射
_KEYWORD_RESPONSES: dict[str, str] = {
    "保险": (
        "[Demo/演示] 保险是一种重要的风险转移工具。华安保险提供多种保险产品，"
        "包括医疗险、重疾险、意外险、年金险、寿险和车险等。\n\n"
        "选择保险产品时，建议根据客户的年龄、家庭状况、收入水平和保障需求来综合评估。"
        "一般建议先配置基础保障型产品（如医疗险和意外险），再考虑储蓄型和理财型产品。\n\n"
        "如需了解具体产品的保障范围、保费和理赔流程，请告诉我更多细节。"
    ),
    "医疗": (
        "[Demo/演示] 医疗险是健康险中最基础的保障产品，主要覆盖因疾病或意外"
        "导致的医疗费用。\n\n"
        "华安保险的百万医疗险产品特点：\n"
        "• 保障额度：最高 600 万\n"
        "• 免赔额：一般 1 万元/年\n"
        "• 保障范围：住院医疗、特殊门诊、门诊手术等\n"
        "• 年龄限制：0-65 周岁可投保\n"
        "• 保费优势：年轻人年保费仅数百元\n\n"
        "推荐搭配重疾险使用，医疗险报销实际费用，重疾险提供一次性赔付用于康复和收入补偿。"
    ),
    "重疾": (
        "[Demo/演示] 重疾险（重大疾病保险）在被保险人确诊合同约定的重大疾病时，"
        "一次性给付保险金。\n\n"
        "华安重疾险产品亮点：\n"
        "• 覆盖 120+ 种重大疾病\n"
        "• 含轻度/中度疾病保障，最高赔付 3 次\n"
        "• 被保人豁免：确诊轻/中症后免交后续保费\n"
        "• 灵活缴费期限：10/20/30 年可选\n"
        "• 身故责任可选附加\n\n"
        "重疾险的意义不仅在于医疗费用覆盖，更在于弥补因患病导致的收入中断和后期康复费用。"
        "建议保额至少为年收入的 3-5 倍。"
    ),
    "意外": (
        "[Demo/演示] 意外险保障因意外事故导致的身故、伤残和医疗费用。"
        "华安意外险产品线丰富：\n\n"
        "1. 综合意外险：\n"
        "   - 意外身故/伤残最高 100 万\n"
        "   - 意外医疗最高 5 万\n"
        "   - 住院津贴 100 元/天\n\n"
        "2. 交通意外险：\n"
        "   - 覆盖航空、高铁、自驾等场景\n"
        "   - 春节出行特别版保费优惠\n\n"
        "3. 学生平安保险：\n"
        "   - 专为在校学生设计\n"
        "   - 保费低、保障全面\n\n"
        "意外险是性价比最高的保险产品之一，建议全家配置。"
    ),
    "年金": (
        "[Demo/演示] 年金险是一种长期储蓄和养老规划工具，"
        "在约定时间开始按期领取年金。\n\n"
        "华安年金险产品优势：\n"
        "• 确定性：收益写进合同，安全稳健\n"
        "• 灵活性：支持减保、保单贷款\n"
        "• 传承功能：可指定受益人，实现财富传承\n"
        "• 复利增值：长期持有收益可观\n\n"
        "适用场景：\n"
        "1. 养老规划：退休后补充养老金\n"
        "2. 教育金储备：为孩子积累教育资金\n"
        "3. 资产配置：作为家庭资产的安全垫\n\n"
        "建议用不超过家庭可投资资产 30% 配置年金险。"
    ),
    "寿险": (
        "[Demo/演示] 寿险以身故为赔付条件，是家庭责任的体现。"
        "华安寿险产品包括：\n\n"
        "1. 定期寿险：\n"
        "   - 保障期限灵活：10/20/30 年或保至 60/70 岁\n"
        "   - 低保费、高保额\n"
        "   - 适合有房贷、子女教育的家庭经济支柱\n\n"
        "2. 终身寿险：\n"
        "   - 终身保障\n"
        "   - 具储蓄和财富传承功能\n"
        "   - 保单现金价值稳步增长\n\n"
        "寿险保额建议 = 房贷余额 + 子女教育费用 + 家庭 5 年生活开支 + 父母赡养费用。"
        "这是对家人最负责任的保障安排。"
    ),
    "车险": (
        "[Demo/演示] 车险是车主必备的保障，华安车险提供全面的车险服务：\n\n"
        "交强险（必买）：\n"
        "• 死亡伤残赔偿限额 18 万\n"
        "• 医疗费用赔偿限额 1.8 万\n"
        "• 财产损失赔偿限额 2000 元\n\n"
        "商业车险推荐组合：\n"
        "• 第三者责任险：建议 200-300 万保额\n"
        "• 车辆损失险：覆盖本车损失\n"
        "• 车上人员责任险：保障车内乘客\n"
        "• 医保外用药责任险：补充三者医疗\n\n"
        "华安车险特色服务：\n"
        "• 7×24 小时在线理赔\n"
        "• 小额案件 1 小时快赔\n"
        "• 免费道路救援\n"
        "• 上门收理赔资料"
    ),
}

_DEFAULT_RESPONSE = (
    "[Demo/演示] 您好！我是安诊保 AI 副驾，华安保险的智能产品助手。\n\n"
    "我可以帮您了解华安保险的各类产品信息，包括：\n"
    "• 医疗险 —— 百万医疗、门诊险等\n"
    "• 重疾险 —— 重大疾病保障\n"
    "• 意外险 —— 综合意外、交通意外等\n"
    "• 年金险 —— 养老规划、教育金\n"
    "• 寿险 —— 定期寿险、终身寿险\n"
    "• 车险 —— 交强险+商业险\n\n"
    "请问您想了解哪类保险产品？或者有具体的保险问题需要咨询？"
)


class MockProvider:
    """演示模式 AI Provider，返回预设的保险相关回复。"""

    def __init__(self, *, delay_ms: int | None = None):
        self._delay_ms = delay_ms  # None 表示随机延迟 300-800ms

    async def _simulate_delay(self) -> int:
        """模拟网络延迟，返回实际延迟毫秒数。"""
        if self._delay_ms is not None:
            ms = self._delay_ms
        else:
            ms = random.randint(300, 800)
        await asyncio.sleep(ms / 1000.0)
        return ms

    def _match_response(self, text: str) -> str:
        """根据关键词匹配回复内容。"""
        for keyword, response in _KEYWORD_RESPONSES.items():
            if keyword in text:
                return response
        return _DEFAULT_RESPONSE

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
        stream: bool = False,
        **kwargs,
    ) -> AIResponse | AsyncIterator[str]:
        """模拟 Chat 接口。"""
        # 从最后一条 user 消息中提取文本
        user_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break

        content = self._match_response(user_text)

        if stream:
            return self._stream_response(content, model=model)

        latency = await self._simulate_delay()
        return AIResponse(
            content=content,
            model=model or "mock-chat",
            prompt_tokens=len(user_text) * 2,  # 粗略估算
            completion_tokens=len(content),
            latency_ms=latency,
            request_id=str(uuid.uuid4()),
        )

    async def _stream_response(self, content: str, *, model: str | None = None) -> AsyncIterator[str]:
        """逐 token 流式输出，带小延迟模拟。"""
        # 先模拟一点初始延迟
        await asyncio.sleep(0.15)

        # 按字符逐个 yield，但每 2-4 个字一组以更自然
        chunk_size = random.choice([2, 3, 4])
        i = 0
        while i < len(content):
            chunk = content[i : i + chunk_size]
            yield chunk
            i += chunk_size
            await asyncio.sleep(random.uniform(0.02, 0.06))

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
        **kwargs,
    ) -> EmbedResponse:
        """生成确定性伪向量（基于 MD5 哈希）。"""
        latency = await self._simulate_delay()
        dim = 1536
        embeddings: list[list[float]] = []
        total_chars = 0

        for text in texts:
            total_chars += len(text)
            vec = [0.0] * dim
            # 用 MD5 哈希生成确定性值
            md5 = hashlib.md5(text.encode("utf-8")).digest()
            for i in range(dim):
                # 循环使用 MD5 的字节来填充 1536 维
                byte_idx = i % len(md5)
                vec[i] = (md5[byte_idx] / 255.0) * 2.0 - 1.0  # 归一化到 [-1, 1]
            embeddings.append(vec)

        return EmbedResponse(
            embeddings=embeddings,
            model=model or "mock-embed",
            prompt_tokens=total_chars * 2,
            latency_ms=latency,
        )

    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str | None = None,
        top_k: int = 5,
        **kwargs,
    ) -> list[RerankResult]:
        """模拟重排序：返回倒序，相关性线性递减。"""
        latency = await self._simulate_delay()
        n = min(top_k, len(documents))
        results: list[RerankResult] = []

        for rank in range(n):
            # 倒序：最后一篇文档得分最高
            doc_index = len(documents) - 1 - rank
            score = round(1.0 - rank * 0.1, 2)
            if score < 0:
                score = 0.0
            results.append(
                RerankResult(
                    index=doc_index,
                    relevance_score=score,
                    document=documents[doc_index],
                )
            )

        return results
