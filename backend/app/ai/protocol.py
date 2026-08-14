from typing import Protocol, AsyncIterator, runtime_checkable
from dataclasses import dataclass, field


@dataclass
class AIResponse:
    """AI 统一响应结构"""
    content: str
    structured_output: dict | None = None
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    request_id: str = ""


@dataclass
class EmbedResponse:
    """Embedding 响应"""
    embeddings: list[list[float]]
    model: str = ""
    prompt_tokens: int = 0
    latency_ms: int = 0


@dataclass
class RerankResult:
    """重排序结果"""
    index: int
    relevance_score: float
    document: str
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class AIProvider(Protocol):
    """AI Provider 统一协议"""

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
        ...

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
        **kwargs,
    ) -> EmbedResponse:
        ...

    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str | None = None,
        top_k: int = 5,
        **kwargs,
    ) -> list[RerankResult]:
        ...
