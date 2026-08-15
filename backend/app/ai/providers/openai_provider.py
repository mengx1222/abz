import math
import time
import uuid
from typing import AsyncIterator

import httpx
from structlog import get_logger

from app.ai.protocol import AIResponse, EmbedResponse, RerankResult
from app.core.config import settings

logger = get_logger()


class OpenAIProvider:
    """OpenAI 兼容 API Provider（支持 DeepSeek、Qwen、OpenAI 等）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "",
        embedding_model: str = "",
        timeout: float = 30.0,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._embedding_model = embedding_model
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    async def close(self):
        """关闭 HTTP 客户端。"""
        await self._client.aclose()

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
        """调用 OpenAI 兼容的 Chat Completions 接口。"""
        use_model = model or self._model or "gpt-3.5-turbo"
        payload: dict = {
            "model": use_model,
            "messages": messages,
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()

        if stream:
            return self._stream_chat(payload, model=use_model, request_id=request_id)

        try:
            resp = await self._client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "openai_chat_error",
                status=e.response.status_code,
                body=e.response.text[:500],
                request_id=request_id,
            )
            raise RuntimeError(f"AI API 错误 {e.response.status_code}: {e.response.text[:200]}") from e
        except httpx.RequestError as e:
            logger.error("openai_chat_connection_error", error=str(e), request_id=request_id)
            raise RuntimeError(f"AI API 连接失败: {e}") from e

        latency_ms = int((time.perf_counter() - t0) * 1000)
        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})

        content = choice.get("message", {}).get("content", "")
        # 解析 structured output
        structured = None
        if response_format and response_format.get("type") == "json_object":
            import json
            try:
                structured = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                pass

        return AIResponse(
            content=content,
            structured_output=structured,
            model=data.get("model", use_model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            request_id=request_id,
        )

    async def _stream_chat(
        self,
        payload: dict,
        *,
        model: str,
        request_id: str,
    ) -> AsyncIterator[str]:
        """流式读取 SSE 响应。"""
        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    import json
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
        except httpx.HTTPStatusError as e:
            logger.error(
                "openai_stream_error",
                status=e.response.status_code,
                body=e.response.text[:500],
                request_id=request_id,
            )
            raise RuntimeError(f"AI 流式 API 错误 {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("openai_stream_connection_error", error=str(e), request_id=request_id)
            raise RuntimeError(f"AI 流式连接失败: {e}") from e

    # ------------------------------------------------------------------
    # Embed
    # ------------------------------------------------------------------

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
        **kwargs,
    ) -> EmbedResponse:
        """调用 OpenAI 兼容的 Embeddings 接口。"""
        use_model = model or self._embedding_model or "text-embedding-3-small"
        payload = {
            "model": use_model,
            "input": texts,
        }
        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()

        try:
            resp = await self._client.post("/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "openai_embed_error",
                status=e.response.status_code,
                body=e.response.text[:500],
                request_id=request_id,
            )
            raise RuntimeError(f"Embedding API 错误 {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("openai_embed_connection_error", error=str(e), request_id=request_id)
            raise RuntimeError(f"Embedding API 连接失败: {e}") from e

        latency_ms = int((time.perf_counter() - t0) * 1000)
        usage = data.get("usage", {})

        # 按 index 排序确保顺序正确
        sorted_data = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        embeddings = [item.get("embedding", []) for item in sorted_data]

        # pgvector 列维度固定（默认 1536）。真实 Provider（如 text-embedding-v3=1024 维）
        # 返回维度不足时统一补齐（尾部补零，余弦相似度保持不变）——否则写库报维度错误。
        target_dim = settings.AI_EMBEDDING_DIM
        if target_dim and embeddings:
            padded: list[list[float]] = []
            for emb in embeddings:
                if len(emb) < target_dim:
                    emb = emb + [0.0] * (target_dim - len(emb))
                elif len(emb) > target_dim:
                    emb = emb[:target_dim]
                padded.append(emb)
            embeddings = padded

        return EmbedResponse(
            embeddings=embeddings,
            model=data.get("model", use_model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            latency_ms=latency_ms,
        )

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
        """调用 Rerank 接口，失败时回退到 embedding 余弦相似度。"""
        request_id = str(uuid.uuid4())
        t0 = time.perf_counter()

        # 尝试调用原生 rerank 端点
        try:
            payload = {
                "model": model or "",
                "query": query,
                "documents": documents,
                "top_n": top_k,
            }
            resp = await self._client.post("/rerank", json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

            latency_ms = int((time.perf_counter() - t0) * 1000)
            results = data.get("results", [])
            return [
                RerankResult(
                    index=r.get("index", 0),
                    relevance_score=r.get("relevance_score", 0.0),
                    document=documents[r.get("index", 0)] if r.get("index", 0) < len(documents) else "",
                    metadata=r.get("metadata", {}),
                )
                for r in results[:top_k]
            ]
        except Exception as e:
            logger.warning(
                "rerank_fallback_to_cosine",
                error=str(e),
                request_id=request_id,
            )

        # 回退：使用 embedding 余弦相似度
        return await self._cosine_rerank_fallback(query, documents, top_k)

    async def _cosine_rerank_fallback(
        self,
        query: str,
        documents: list[str],
        top_k: int,
    ) -> list[RerankResult]:
        """使用 embedding 余弦相似度作为 rerank 回退方案。"""
        all_texts = [query] + documents
        embed_resp = await self.embed(all_texts)
        query_vec = embed_resp.embeddings[0]
        doc_vecs = embed_resp.embeddings[1:]

        scored: list[tuple[int, float]] = []
        for i, dvec in enumerate(doc_vecs):
            score = self._cosine_sim(query_vec, dvec)
            scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            RerankResult(
                index=idx,
                relevance_score=round(score, 4),
                document=documents[idx],
            )
            for idx, score in scored[:top_k]
        ]

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """计算两个向量的余弦相似度。"""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

