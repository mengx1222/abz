import asyncio
import time
from typing import AsyncIterator

from structlog import get_logger

from app.ai.protocol import AIProvider, AIResponse, EmbedResponse, RerankResult
from app.ai.providers import MockProvider, OpenAIProvider
from app.core.config import settings

logger = get_logger()

# 全局单例
_ai_gateway: "AIGateway | None" = None


def get_ai_gateway() -> "AIGateway":
    """获取全局 AIGateway 单例。"""
    global _ai_gateway
    if _ai_gateway is None:
        _ai_gateway = AIGateway()
    return _ai_gateway


class AIGateway:
    """AI Gateway —— 统一入口，根据配置路由到对应的 Provider。"""

    def __init__(self) -> None:
        self._provider: AIProvider | None = None
        self._provider_name: str = settings.AI_PROVIDER
        self._lock = asyncio.Lock()

    async def _ensure_provider(self) -> AIProvider:
        """懒初始化 Provider（线程安全）。"""
        if self._provider is not None:
            return self._provider

        async with self._lock:
            # double-check
            if self._provider is not None:
                return self._provider

            self._provider = self._create_provider()
            logger.info(
                "ai_gateway_provider_initialized",
                provider=self._provider_name,
            )
            return self._provider

    def _create_provider(self) -> AIProvider:
        """根据配置创建 Provider 实例。"""
        name = self._provider_name.lower().strip()

        if name == "mock":
            return MockProvider()

        # 其他情况均视为 OpenAI 兼容 API（deepseek / qwen / openai 等）
        if not settings.AI_API_KEY:
            logger.warning(
                "ai_gateway_missing_api_key",
                provider=name,
                fallback="mock",
            )
            return MockProvider()

        if not settings.AI_BASE_URL:
            logger.warning(
                "ai_gateway_missing_base_url",
                provider=name,
                fallback="mock",
            )
            return MockProvider()

        return OpenAIProvider(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            model=settings.AI_MODEL,
            embedding_model=settings.AI_EMBEDDING_MODEL,
        )

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

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
        """调用 Chat 接口。"""
        provider = await self._ensure_provider()
        t0 = time.perf_counter()

        try:
            result = await provider.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                stream=stream,
                **kwargs,
            )
        except Exception as e:
            logger.error(
                "ai_gateway_chat_error",
                provider=self._provider_name,
                model=model,
                error=str(e),
            )
            raise

        # 非流式时记录日志
        if not stream and isinstance(result, AIResponse):
            latency = result.latency_ms or int((time.perf_counter() - t0) * 1000)
            logger.info(
                "ai_gateway_chat",
                provider=self._provider_name,
                model=result.model or model,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                latency_ms=latency,
                stream=False,
            )

        return result

    # ------------------------------------------------------------------
    # Embed
    # ------------------------------------------------------------------

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
        **kwargs,
    ) -> EmbedResponse:
        """调用 Embedding 接口。"""
        provider = await self._ensure_provider()
        t0 = time.perf_counter()

        try:
            result = await provider.embed(texts=texts, model=model, **kwargs)
        except Exception as e:
            logger.error(
                "ai_gateway_embed_error",
                provider=self._provider_name,
                error=str(e),
            )
            raise

        latency = result.latency_ms or int((time.perf_counter() - t0) * 1000)
        logger.info(
            "ai_gateway_embed",
            provider=self._provider_name,
            model=result.model or model,
            text_count=len(texts),
            prompt_tokens=result.prompt_tokens,
            latency_ms=latency,
        )

        return result

    # ------------------------------------------------------------------
    # Rerank
    # ------------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str | None = None,
        top_k: int = 5,
        **kwargs,
    ) -> list[RerankResult]:
        """调用 Rerank 接口。"""
        provider = await self._ensure_provider()
        t0 = time.perf_counter()

        try:
            result = await provider.rerank(
                query=query,
                documents=documents,
                model=model,
                top_k=top_k,
                **kwargs,
            )
        except Exception as e:
            logger.error(
                "ai_gateway_rerank_error",
                provider=self._provider_name,
                error=str(e),
            )
            raise

        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "ai_gateway_rerank",
            provider=self._provider_name,
            doc_count=len(documents),
            top_k=len(result),
            latency_ms=latency_ms,
        )

        return result
