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

from sqlalchemy import func, select, text, or_, and_, cast
from sqlalchemy.dialects.postgresql import UUID
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
        query_embedding: list[float] | None = None,  # Demo 模式忽略（兼容 pipeline.query 统一签名）
        top_k: int = RERANK_TOP_K,
        knowledge_base_ids: list[str] | None = None,
        user_roles: list[str] | None = None,
        org_id: str | None = None,
        accessible_org_ids: list[str] | None = None,
        effective_only: bool = True,
        product_type: str | None = None,
    ) -> list[SearchResult]:
        """基于关键词匹配的简单检索。

        评分策略：
        1. 每个匹配的关键词得分
        2. 标题匹配加分
        3. 按总分排序
        4. 可选日期有效性过滤
        5. 可选产品边界过滤（product_type 元数据精确匹配，缺失时按标题回退）
        6. 权限过滤（与生产检索器同语义）：
           - allowed_roles：chunk 携带 kb_allowed_roles（None=全员；非 None=角色须在数组内）
           - 组织范围：chunk 携带 kb_org_id（None=未限定组织的共享知识库；非 None 须命中
             accessible_org_ids / org_id），`["__ALL__"]` 表示全量
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

            # ---- 权限过滤（与生产 SQL WHERE 层同语义） ----
            # 角色过滤：空角色列表 = 无任何角色被允许 → 全拒；
            # kb_allowed_roles None → 全员；非 None → 用户角色须命中
            if user_roles is not None:
                if not user_roles:
                    continue
                kb_roles = chunk.get("kb_allowed_roles")
                if kb_roles is not None and not any(r in kb_roles for r in user_roles):
                    continue
            # 组织范围过滤：kb_org_id None → 未限定组织的共享知识库（仍受角色约束）；
            # 非 None → 必须命中可访问组织集合（__ALL__ 表示全量）。
            if accessible_org_ids is not None and "__ALL__" not in accessible_org_ids:
                kb_org = chunk.get("kb_org_id")
                if kb_org and kb_org not in accessible_org_ids:
                    continue
            elif org_id is not None:
                # 兼容：未传 accessible_org_ids 时按单组织匹配
                kb_org = chunk.get("kb_org_id")
                if kb_org and kb_org != org_id:
                    continue

            # 产品边界过滤：明确请求产品时，仅保留产品匹配的 chunk。
            # 有 product_type 元数据 → 精确匹配；缺失 → 按文档标题包含产品名回退，
            # 避免"保险"等共同词把同领域错误产品当成有效依据。
            if product_type:
                meta = chunk.get("metadata", {}) or {}
                chunk_product = meta.get("product_type")
                if chunk_product:
                    if chunk_product != product_type:
                        continue
                elif product_type not in title:
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
                    # 携带 KB 权限元数据（与生产检索器一致，供 citation/二次校验）
                    "kb_allowed_roles": chunk.get("kb_allowed_roles"),
                    "kb_org_id": chunk.get("kb_org_id"),
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
        accessible_org_ids: list[str] | None = None,
        product_type: str | None = None,
    ) -> list[SearchResult]:
        """执行混合检索。

        1. 向量检索 (cosine similarity)
        2. BM25 全文检索
        3. RRF 融合
        4. 权限过滤（SQL WHERE 层主过滤 + 召回后二次校验）
        5. 文档版本日期过滤
        6. 产品边界过滤（product_type，仅保留产品匹配的知识依据）

        权限语义：
        - user_roles：角色白名单。为 None 时不限制角色；空列表 `[]` 表示
          「无任何角色被允许」→ 全部拒答（调用方无法提供用户上下文时使用）。
        - accessible_org_ids：`DataPermissionChecker.filter_accessible_org_ids()`
          产出，`["__ALL__"]` 表示全量可见（SYSTEM_ADMIN）。
        - org_id：兼容参数（单组织快捷方式），仅当 accessible_org_ids 未传时生效。
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
            accessible_org_ids=accessible_org_ids,
            user_roles=user_roles,
            product_type=product_type,
        )

        # Step 2: BM25检索
        bm25_results = await self._bm25_search(
            query, top_k=BM25_SEARCH_TOP_K,
            knowledge_base_ids=knowledge_base_ids,
            effective_now=now, org_id=org_id,
            accessible_org_ids=accessible_org_ids,
            user_roles=user_roles,
            product_type=product_type,
        )

        # Step 3: RRF融合
        fused = self._rrf_fusion(vector_results, bm25_results)

        # Step 4: 权限二次校验（纵深防御，防任何绕过 SQL 条件的路径）
        # SQL 层已按 user_roles / accessible_org_ids 过滤，此处基于召回结果携带的
        # KB 权限元数据再校验一次；user_roles=[]（空角色）时直接拒绝全部。
        if user_roles is not None:
            fused = self._filter_by_permission(fused, user_roles, accessible_org_ids)

        # Step 5: 取 top_k
        return fused[:top_k]

    @staticmethod
    def _product_boundary_condition(product_type: str):
        """构造产品边界 SQL 过滤条件。

        优先匹配 chunk metadata.product_type（JSONB ->>），
        缺失时回退到文档标题包含产品名——避免"保险"等共同词
        把同领域错误产品召回为有效依据（如"车险"不得命中医疗险文档）。
        """
        return or_(
            DocumentChunk.metadata_["product_type"].astext == product_type,
            and_(
                DocumentChunk.metadata_["product_type"].astext.is_(None),
                Document.title.like(f"%{product_type}%"),
            ),
        )

    @staticmethod
    def _permission_conditions(
        user_roles: list[str] | None,
        accessible_org_ids: list[str] | None,
        org_id: str | None = None,
    ) -> list:
        """构造 RAG 权限 SQL WHERE 条件（与 product_boundary / effective_date 同级）。

        - 角色：`allowed_roles IS NULL`（全员）或 `allowed_roles ? role_code`（jsonb 存在）；
          逐角色 OR 组合；user_roles=[]（空列表）→ 返回 `false()`（物理上全拒）。
        - 组织：`organization_id IS NULL`（未限定组织的共享知识库）或
          `organization_id IN (accessible_org_ids)`；`["__ALL__"]` 跳过组织条件。
          仅当 accessible_org_ids 未传时回退 org_id 单组织匹配。

        该方法纯构造，不执行查询，便于单元测试编译断言。
        """
        conditions: list = []

        # ---- 角色过滤（allowed_roles） ----
        if user_roles is not None:
            if not user_roles:
                # 空角色列表：无任何角色被允许 → 恒假条件（全拒）
                conditions.append(text("false"))
            else:
                role_cond = or_(
                    KnowledgeBase.allowed_roles.is_(None),
                    or_(
                        *(KnowledgeBase.allowed_roles.op("?")(role) for role in user_roles)
                    ),
                )
                conditions.append(role_cond)

        # ---- 组织范围过滤（organization_id） ----
        org_ids = None
        if accessible_org_ids is not None:
            if "__ALL__" not in accessible_org_ids:
                org_ids = [uuid.UUID(o) for o in accessible_org_ids if o]
        elif org_id:
            try:
                org_ids = [uuid.UUID(org_id)]
            except (ValueError, TypeError):
                org_ids = None
        if org_ids is not None:
            conditions.append(
                or_(
                    KnowledgeBase.organization_id.is_(None),
                    KnowledgeBase.organization_id.in_(org_ids),
                )
            )

        return conditions

    async def _vector_search(
        self,
        embedding: list[float] | None,
        top_k: int,
        knowledge_base_ids: list[str] | None,
        effective_now: datetime | None = None,
        org_id: str | None = None,
        accessible_org_ids: list[str] | None = None,
        user_roles: list[str] | None = None,
        product_type: str | None = None,
    ) -> list[dict]:
        """pgvector cosine距离检索。

        权限过滤在 SQL WHERE 层完成（JOIN KnowledgeBase + 角色/组织条件），
        禁止"先召回全部再 Python 过滤"。
        """
        if embedding is None:
            return []

        # pgvector 的 cosine_distance 需要 vector 类型参数：
        # - SQLAlchemy 传 list → asyncpg 拒绝（expected str, got list）
        # - 传 VARCHAR 字符串 → cosine_distance(vector, varchar) 不存在
        # - text(":vec::vector") bindparam → SQLAlchemy 无法解析
        # 因此直接构造 vector 字面量 "'[1,2,...]'::vector"（embedding 为程序内部 float 列表，拼接安全）
        embedding_literal = text("'" + "[" + ",".join(str(x) for x in embedding) + "]'::vector")

        # 构建基础查询
        stmt = (
            select(
                DocumentChunk.__table__.c.id,
                DocumentChunk.__table__.c.document_id,
                DocumentChunk.__table__.c.content,
                DocumentChunk.__table__.c["metadata"],
                Document.knowledge_base_id.label("kb_id"),
                KnowledgeBase.allowed_roles.label("kb_allowed_roles"),
                KnowledgeBase.organization_id.label("kb_org_id"),
                # 1 - cosine_distance 作为相似度分数
                (1 - func.cosine_distance(DocumentChunk.embedding, embedding_literal)).label("score"),
            )
            .where(DocumentChunk.embedding.isnot(None))
            .where(~Document.is_deleted)
            .where(Document.status == "published")
            .join(Document, DocumentChunk.document_id == Document.id)
            .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
        )

        # 文档版本过滤：生效/失效日期
        if effective_now is not None:
            stmt = stmt.where(
                or_(Document.effective_date.is_(None), Document.effective_date <= effective_now)
            )
            stmt = stmt.where(
                or_(Document.expiry_date.is_(None), Document.expiry_date > effective_now)
            )

        # 权限过滤（角色 + 组织范围）：SQL WHERE 层
        for cond in self._permission_conditions(user_roles, accessible_org_ids, org_id):
            stmt = stmt.where(cond)

        # knowledge_base_ids 过滤
        if knowledge_base_ids:
            kb_uuids = [uuid.UUID(kid) for kid in knowledge_base_ids if kid]
            if kb_uuids:
                stmt = stmt.where(Document.knowledge_base_id.in_(kb_uuids))

        # 产品边界过滤：明确请求产品时仅保留产品匹配的 chunk
        if product_type:
            stmt = stmt.where(self._product_boundary_condition(product_type))

        stmt = stmt.order_by(text("score DESC")).limit(top_k)

        try:
            result = await self.db.execute(stmt)
            rows = result.all()
            return [
                {
                    "chunk_id": str(row.id),
                    "document_id": str(row.document_id),
                    "content": row.content,
                    "metadata": {
                        **(row._mapping.get("metadata") or {}),
                        # 携带 KB 权限元数据供召回后二次校验（_filter_by_permission）
                        "kb_allowed_roles": row.kb_allowed_roles,
                        "kb_org_id": str(row.kb_org_id) if row.kb_org_id else None,
                        # 归属知识库（RRF 融合 / citation 依赖）
                        "knowledge_base_id": str(row.kb_id) if row.kb_id else "",
                    },
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
        accessible_org_ids: list[str] | None = None,
        user_roles: list[str] | None = None,
        product_type: str | None = None,
    ) -> list[dict]:
        """PostgreSQL 全文检索 (tsvector + GIN)。

        权限过滤在 SQL WHERE 层完成（JOIN KnowledgeBase + 角色/组织条件）。
        """
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
                Document.knowledge_base_id.label("kb_id"),
                KnowledgeBase.allowed_roles.label("kb_allowed_roles"),
                KnowledgeBase.organization_id.label("kb_org_id"),
                func.ts_rank(search_col, search_text).label("score"),
            )
            .where(search_col.op("@@")(search_text))
            .where(~Document.is_deleted)
            .where(Document.status == "published")
            .join(Document, DocumentChunk.document_id == Document.id)
            .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
        )

        # 文档版本过滤：生效/失效日期
        if effective_now is not None:
            stmt = stmt.where(
                or_(Document.effective_date.is_(None), Document.effective_date <= effective_now)
            )
            stmt = stmt.where(
                or_(Document.expiry_date.is_(None), Document.expiry_date > effective_now)
            )

        # 权限过滤（角色 + 组织范围）：SQL WHERE 层
        for cond in self._permission_conditions(user_roles, accessible_org_ids, org_id):
            stmt = stmt.where(cond)

        # knowledge_base_ids 过滤
        if knowledge_base_ids:
            kb_uuids = [uuid.UUID(kid) for kid in knowledge_base_ids if kid]
            if kb_uuids:
                stmt = stmt.where(Document.knowledge_base_id.in_(kb_uuids))

        # 产品边界过滤：明确请求产品时仅保留产品匹配的 chunk
        if product_type:
            stmt = stmt.where(self._product_boundary_condition(product_type))

        stmt = stmt.order_by(text("score DESC")).limit(top_k)

        try:
            result = await self.db.execute(stmt)
            rows = result.all()
            return [
                {
                    "chunk_id": str(row.id),
                    "document_id": str(row.document_id),
                    "content": row.content,
                    "metadata": {
                        **(row._mapping.get("metadata") or {}),
                        # 携带 KB 权限元数据供召回后二次校验（_filter_by_permission）
                        "kb_allowed_roles": row.kb_allowed_roles,
                        "kb_org_id": str(row.kb_org_id) if row.kb_org_id else None,
                        # 归属知识库（RRF 融合 / citation 依赖）
                        "knowledge_base_id": str(row.kb_id) if row.kb_id else "",
                    },
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
            # RRF 原始分 1/(k+rank) 量级过小（k=60 单命中约 0.016），
            # 而 pipeline.MIN_CONTEXT_SCORE=0.3 是给原始向量/BM25 分数的阈值。
            # 统一放大 100 倍，使 RRF 分数与原始分数同量级，保持拒答门控语义。
            rrf_score = (info.get("rrf_vector", 0) + info.get("rrf_bm25", 0)) * 100.0
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
        accessible_org_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        """根据用户角色/组织范围过滤检索结果（召回后二次校验）。

        主过滤在 SQL WHERE 层完成；本方法作为纵深防御，基于召回结果携带的
        KB 权限元数据（metadata.kb_allowed_roles / metadata.kb_org_id）再次校验，
        防止任何绕过 SQL 条件的路径把越权文档带入最终集合。

        - user_roles：空列表 → 全部拒绝（调用方无法提供用户上下文）。
        - 未携带权限元数据的结果（如旧数据/外部构造）不额外拦截（SQL 层已保证）。
        - 日志仅记录 filtered_count，不记录被过滤正文。
        """
        if not user_roles:
            if results:
                logger.warning("rag_permission_secondary_check", filtered_count=len(results))
            return []

        allowed = []
        filtered = 0
        for r in results:
            kb_roles = r.metadata.get("kb_allowed_roles")
            if kb_roles is not None and not any(role in kb_roles for role in user_roles):
                filtered += 1
                continue
            if accessible_org_ids and "__ALL__" not in accessible_org_ids:
                kb_org = r.metadata.get("kb_org_id")
                if kb_org and kb_org not in accessible_org_ids:
                    filtered += 1
                    continue
            allowed.append(r)

        if filtered:
            logger.info("rag_permission_secondary_check", filtered_count=filtered)
        return allowed


# 需要导入DocumentChunk、Document、KnowledgeBase
from app.models.knowledge import DocumentChunk, Document, KnowledgeBase

