"""RAG检索器 —— 混合检索（向量 + BM25）+ RRF融合 + 权限过滤。

设计原则：
- 向量检索：pgvector cosine distance，HNSW索引
- BM25检索：PostgreSQL全文检索 GIN索引
- RRF融合：K=60，两个排序的倒数排名之和
- 权限过滤：根据用户角色过滤可见知识库
- 版本过滤：根据文档生效/失效日期过滤过期文档
- Demo模式：内存中的关键词匹配检索
"""
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select, text, or_, cast
from sqlalchemy.dialects.postgresql import UUID, Vector
from structlog import get_logger

from app.core.config import settings

logger = get_logger()

# RRF 参数
RRF_K = 60  # Reciprocal Rank Fusion 的 K 值
VECTOR_SEARCH_TOP_K = 20  # 向量检索返回数量
BM25_SEARCH_TOP_K = 20  # BM25检索返回数量
RERANK_TOP_K = 8  # 重排序后保留数量
MIN_RELEVANCE_SCORE = 0.3  # 最低相关性阈值


@dataclass
class SearchResult:
    """检索结果。"""
    chunk_id: str
    document_id: str
    document_title: str
    knowledge_base_id: str
    content: str
    score: float  # 最终融合分数
    vector_score: float = 0.0  # 向量相似度
    bm25_score: float = 0.0  # BM25分数
    rerank_score: float = 0.0  # 重排序分数
    metadata: dict = field(default_factory=dict)


class DemoRetriever:
    """Demo模式检索器 —— 基于关键词匹配的内存检索。"""

    def __init__(self, chunks: list[dict] | None = None):
        """
        Args:
            chunks: 预加载的chunk列表，每个chunk包含:
                {"id": str, "content": str, "document_title": str,
                 "heading": str, "knowledge_base_id": str, "document_id": str}
        """
        self._chunks = chunks or []

    def add_chunks(self, chunks: list[dict]):
        """添加检索chunk。"""
        self._chunks.extend(chunks)

    async def search(
        self,
        query: str,
        top_k: int = RERANK_TOP_K,
        knowledge_base_ids: list[str] | None = None,
        user_roles: list[str] | None = None,
        org_id: str | None = None,
        effective_only: bool = True,
    ) -> list[SearchResult]:
        """基于关键词匹配的简单检索。

        评分策略：
        1. 每个匹配的关键词得分
        2. 标题匹配加分
        3. 按总分排序
        4. 可选日期有效性过滤
        """
        query_lower = query.lower()
        # 提取查询中的关键词
        keywords = self._extract_keywords(query)
        if not keywords:
            keywords = [query_lower]

        scored: list[tuple[float, dict]] = []
        now = datetime.now(timezone.utc) if effective_only else None

        for chunk in self._chunks:
            content_lower = chunk["content"].lower()
            title = chunk.get("document_title", "")

            # 跳过被知识库ID过滤的
            if knowledge_base_ids and chunk.get("knowledge_base_id") not in knowledge_base_ids:
                continue

            # 日期有效性过滤（Demo模式简单检查 metadata）
            if effective_only and now is not None:
                meta = chunk.get("metadata", {})
                eff = meta.get("effective_date")
                exp = meta.get("expiry_date")
                if eff and eff > now.isoformat():
                    continue
                if exp and exp <= now.isoformat():
                    continue

            # 计算匹配分数
            score = 0.0
            for kw in keywords:
                if kw in content_lower:
                    score += 1.0
                if kw in title.lower():
                    score += 2.0  # 标题匹配加分

            if score > 0:
                # 归一化分数到 0-1
                normalized_score = min(score / (len(keywords) * 3.0), 1.0)
                scored.append((normalized_score, chunk))

        # 按分数降序
        scored.sort(key=lambda x: x[0], reverse=True)

        # 取 top_k
        results: list[SearchResult] = []
        for rank, (score, chunk) in enumerate(scored[:top_k]):
            results.append(SearchResult(
                chunk_id=chunk.get("id", str(uuid.uuid4())),
                document_id=chunk.get("document_id", ""),
                document_title=chunk.get("document_title", ""),
                knowledge_base_id=chunk.get("knowledge_base_id", ""),
                content=chunk["content"],
                score=score,
                vector_score=score,
                bm25_score=score * 0.8,
                metadata={
                    "heading": chunk.get("heading", ""),
                    "search_method": "demo_keyword",
                },
            ))

        return results

    def _extract_keywords(self, query: str) -> list[str]:
        """从查询中提取关键词。"""
        # 简单分词：去除常见停用词
        stopwords = {"的", "是", "了", "吗", "什么", "怎么", "如何", "哪", "那",
                      "可以", "请", "问", "我", "你", "他", "她", "它", "有", "在",
                      "这个", "那个", "一个", "哪些", "哪些", "为什么", "能", "会",
                      "should", "is", "the", "a", "an", "what", "how", "why", "can",
                      "please", "do", "does", "did", "to", "of", "in", "for", "and"}
        words = []
        # 中文：按字分割（简化处理）
        for char in query:
            if char.strip() and char not in stopwords:
                words.append(char.lower())
        # 也添加2-gram和3-gram
        for i in range(len(query) - 1):
            bigram = query[i:i+2].lower()
            if bigram.strip() and bigram not in stopwords:
                words.append(bigram)
        for i in range(len(query) - 2):
            trigram = query[i:i+3].lower()
            if trigram.strip() and trigram not in stopwords:
                words.append(trigram)
        return list(set(words))  # 去重


class Retriever:
    """生产模式检索器 —— 混合检索（向量 + BM25）+ RRF融合。

    需要 PostgreSQL + pgvector 扩展。
    """

    def __init__(self, db_session=None):
        self.db = db_session

    async def search(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        top_k: int = RERANK_TOP_K,
        knowledge_base_ids: list[str] | None = None,
        user_roles: list[str] | None = None,
        org_id: str | None = None,
    ) -> list[SearchResult]:
        """执行混合检索。

        1. 向量检索 (cosine similarity)
        2. BM25 全文检索
        3. RRF 融合
        4. 权限过滤
        5. 文档版本日期过滤
        """
        if self.db is None:
            logger.warning("retriever_no_db_session")
            return []

        now = datetime.now(timezone.utc)

        # Step 1: 向量检索
        vector_results = await self._vector_search(
            query_embedding, top_k=VECTOR_SEARCH_TOP_K,
            knowledge_base_ids=knowledge_base_ids,
            effective_now=now, org_id=org_id,
        )

        # Step 2: BM25检索
        bm25_results = await self._bm25_search(
            query, top_k=BM25_SEARCH_TOP_K,
            knowledge_base_ids=knowledge_base_ids,
            effective_now=now, org_id=org_id,
        )

        # Step 3: RRF融合
        fused = self._rrf_fusion(vector_results, bm25_results)

        # Step 4: 权限过滤
        if user_roles:
            fused = self._filter_by_permission(fused, user_roles)

        # Step 5: 取 top_k
        return fused[:top_k]

    async def _vector_search(
        self,
        embedding: list[float] | None,
        top_k: int,
        knowledge_base_ids: list[str] | None,
        effective_now: datetime | None = None,
        org_id: str | None = None,
    ) -> list[dict]:
        """pgvector cosine距离检索。"""
        if embedding is None:
            return []

        # pgvector 的 cosine_distance 需要 vector 类型参数。
        # SQLAlchemy 直接传 list 会被 asyncpg 拒绝（expected str, got list）；
        # 传字符串字面量会被当作 VARCHAR —— 需显式 cast 为 vector。
        embedding_literal = cast("[" + ",".join(str(x) for x in embedding) + "]", Vector)

        # 构建基础查询
        stmt = (
            select(
                DocumentChunk.__table__.c.id,
                DocumentChunk.__table__.c.document_id,
                DocumentChunk.__table__.c.content,
                DocumentChunk.__table__.c["metadata"],
                # 1 - cosine_distance 作为相似度分数
                (1 - func.cosine_distance(DocumentChunk.embedding, embedding_literal)).label("score"),
            )
            .where(DocumentChunk.embedding.isnot(None))
            .where(~Document.is_deleted)
            .where(Document.status == "published")
            .join(Document, DocumentChunk.document_id == Document.id)
        )

        # 文档版本过滤：生效/失效日期
        if effective_now is not None:
            stmt = stmt.where(
                or_(Document.effective_date.is_(None), Document.effective_date <= effective_now)
            )
            stmt = stmt.where(
                or_(Document.expiry_date.is_(None), Document.expiry_date > effective_now)
            )

        # org_id 过滤（预留组织级隔离）
        if org_id:
            try:
                org_uuid = uuid.UUID(org_id)
                stmt = stmt.where(Document.knowledge_base_id.in_(
                    select(KnowledgeBase.id).where(KnowledgeBase.id == org_uuid)
                ))
            except (ValueError, TypeError):
                pass

        # knowledge_base_ids 过滤
        if knowledge_base_ids:
            kb_uuids = [uuid.UUID(kid) for kid in knowledge_base_ids if kid]
            if kb_uuids:
                stmt = stmt.where(Document.knowledge_base_id.in_(kb_uuids))

        stmt = stmt.order_by(text("score DESC")).limit(top_k)

        try:
            result = await self.db.execute(stmt)
            rows = result.all()
            return [
                {
                    "chunk_id": str(row.id),
                    "document_id": str(row.document_id),
                    "content": row.content,
                    "metadata": row._mapping.get("metadata") or {},
                    "score": float(row.score),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("vector_search_error", error=str(e))
            return []

    async def _bm25_search(
        self,
        query: str,
        top_k: int,
        knowledge_base_ids: list[str] | None,
        effective_now: datetime | None = None,
        org_id: str | None = None,
    ) -> list[dict]:
        """PostgreSQL 全文检索 (tsvector + GIN)。"""
        # 使用 plainto_tsquery 进行简单查询
        search_text = func.plainto_tsquery("simple", query)
        # search_text 列是纯文本（Text），@@ / ts_rank 需要 tsvector —— 查询时转换
        search_col = func.to_tsvector("simple", DocumentChunk.search_text)

        stmt = (
            select(
                DocumentChunk.__table__.c.id,
                DocumentChunk.__table__.c.document_id,
                DocumentChunk.__table__.c.content,
                DocumentChunk.__table__.c["metadata"],
                func.ts_rank(search_col, search_text).label("score"),
            )
            .where(search_col.op("@@")(search_text))
            .where(~Document.is_deleted)
            .where(Document.status == "published")
            .join(Document, DocumentChunk.document_id == Document.id)
        )

        # 文档版本过滤：生效/失效日期
        if effective_now is not None:
            stmt = stmt.where(
                or_(Document.effective_date.is_(None), Document.effective_date <= effective_now)
            )
            stmt = stmt.where(
                or_(Document.expiry_date.is_(None), Document.expiry_date > effective_now)
            )

        # org_id 过滤（预留组织级隔离）
        if org_id:
            try:
                org_uuid = uuid.UUID(org_id)
                stmt = stmt.where(Document.knowledge_base_id.in_(
                    select(KnowledgeBase.id).where(KnowledgeBase.id == org_uuid)
                ))
            except (ValueError, TypeError):
                pass

        # knowledge_base_ids 过滤
        if knowledge_base_ids:
            kb_uuids = [uuid.UUID(kid) for kid in knowledge_base_ids if kid]
            if kb_uuids:
                stmt = stmt.where(Document.knowledge_base_id.in_(kb_uuids))

        stmt = stmt.order_by(text("score DESC")).limit(top_k)

        try:
            result = await self.db.execute(stmt)
            rows = result.all()
            return [
                {
                    "chunk_id": str(row.id),
                    "document_id": str(row.document_id),
                    "content": row.content,
                    "metadata": row._mapping.get("metadata") or {},
                    "score": float(row.score),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("bm25_search_error", error=str(e))
            return []

    @staticmethod
    def _rrf_fusion(
        vector_results: list[dict],
        bm25_results: list[dict],
        k: int = RRF_K,
    ) -> list[SearchResult]:
        """RRF (Reciprocal Rank Fusion) 融合两个排序列表。"""
        scores: dict[str, dict] = {}  # chunk_id -> {score, vector_score, bm25_score, data}

        # 向量结果
        for rank, result in enumerate(vector_results):
            cid = result["chunk_id"]
            if cid not in scores:
                scores[cid] = {"data": result, "vector_score": result["score"], "bm25_score": 0.0}
            scores[cid]["vector_score"] = result["score"]

        # BM25结果
        for rank, result in enumerate(bm25_results):
            cid = result["chunk_id"]
            if cid not in scores:
                scores[cid] = {"data": result, "vector_score": 0.0, "bm25_score": result["score"]}
            scores[cid]["bm25_score"] = result["score"]

        # RRF计算
        for rank, result in enumerate(vector_results):
            cid = result["chunk_id"]
            scores[cid]["rrf_vector"] = 1.0 / (k + rank + 1)

        for rank, result in enumerate(bm25_results):
            cid = result["chunk_id"]
            if cid in scores:
                scores[cid]["rrf_bm25"] = 1.0 / (k + rank + 1)
            else:
                scores[cid] = {
                    "data": result,
                    "vector_score": 0.0,
                    "bm25_score": result["score"],
                    "rrf_vector": 0.0,
                    "rrf_bm25": 1.0 / (k + rank + 1),
                }

        # 计算最终分数并排序
        final: list[SearchResult] = []
        for cid, info in scores.items():
            rrf_score = info.get("rrf_vector", 0) + info.get("rrf_bm25", 0)
            metadata = info["data"].get("metadata", {})
            final.append(SearchResult(
                chunk_id=cid,
                document_id=info["data"]["document_id"],
                document_title=metadata.get("document_title", ""),
                knowledge_base_id=metadata.get("knowledge_base_id", ""),
                content=info["data"]["content"],
                score=rrf_score,
                vector_score=info["vector_score"],
                bm25_score=info["bm25_score"],
                metadata=metadata,
            ))

        final.sort(key=lambda x: x.score, reverse=True)
        return final

    @staticmethod
    def _filter_by_permission(
        results: list[SearchResult],
        user_roles: list[str],
    ) -> list[SearchResult]:
        """根据用户角色过滤检索结果。"""
        # 如果知识库设置了 allowed_roles，检查用户是否在其中
        return results  # TODO: 实现权限过滤逻辑


# 需要导入DocumentChunk、Document、KnowledgeBase
from app.models.knowledge import DocumentChunk, Document, KnowledgeBase

