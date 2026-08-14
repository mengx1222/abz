"""RAG Pipeline 编排器 —— 协调解析、分块、嵌入、检索的完整流程。

提供统一的高层接口：
- index_document(): 文档入库（解析→分块→嵌入→存储）
- query(): 查询（检索→重排→上下文组装）
- init_demo_index(): 初始化Demo模式的内存索引
"""
import uuid
from typing import AsyncGenerator

from structlog import get_logger

from app.ai.gateway import get_ai_gateway
from app.core.config import settings
from app.rag.chunker import chunk_document, Chunk
from app.rag.parser import DocumentParser, ParsedDocument, get_demo_documents
from app.rag.retriever import DemoRetriever, Retriever, SearchResult

logger = get_logger()

# Demo模式全局检索器
_demo_retriever: DemoRetriever | None = None

# RAG系统提示词模板
_RAG_SYSTEM_PROMPT_TEMPLATE = """你是「安诊保 AI 副驾」，华安保险的智能保险产品专家助手。

## 你的职责
1. 根据知识库内容准确回答保险产品相关问题
2. 为销售人员提供专业的产品咨询支持
3. 在回答中引用知识来源，确保可追溯

## 回答规范
- 仅基于以下参考内容回答问题，不要编造信息
- 如果参考内容中没有相关信息，明确告知用户
- 使用结构化格式回答（要点列表、表格等）
- 在适当位置标注引用来源 [文档名]
- 保持语言专业但易懂

## 参考内容
{context}
"""

# 拒答阈值
MIN_CONTEXT_SCORE = 0.3


def _build_context(search_results: list[SearchResult], max_chars: int = 4000) -> str:
    """将检索结果组装为LLM的上下文文本。"""
    context_parts = []
    total_chars = 0

    for result in search_results:
        if total_chars >= max_chars:
            break
        doc_title = result.document_title or "未知文档"
        heading = result.metadata.get("heading", "")
        content = result.content

        # 构建引用块
        chunk_text = f"【{doc_title}"
        if heading:
            chunk_text += f" - {heading}"
        chunk_text += f"】(相关度: {result.score:.0%})\n{content}\n"

        if total_chars + len(chunk_text) > max_chars:
            # 截断
            remaining = max_chars - total_chars
            chunk_text = chunk_text[:remaining] + "\n..."
        
        context_parts.append(chunk_text)
        total_chars += len(chunk_text)

    return "\n---\n".join(context_parts)


class RAGPipeline:
    """RAG Pipeline 统一编排器。"""

    def __init__(self, db=None):
        self.db = db
        self.gateway = get_ai_gateway()
        self._retriever: DemoRetriever | Retriever | None = None

    async def _get_retriever(self) -> DemoRetriever | Retriever:
        """获取检索器。"""
        if self._retriever is not None:
            return self._retriever

        if settings.DEMO_MODE or self.db is None:
            global _demo_retriever
            if _demo_retriever is None:
                await init_demo_index()
            self._retriever = _demo_retriever
        else:
            self._retriever = Retriever(db_session=self.db)

        return self._retriever

    async def index_document(
        self,
        content: str,
        file_type: str,
        title: str = "",
        file_name: str = "",
        knowledge_base_id: str = "",
        document_id: str = "",
    ) -> dict:
        """文档入库流程：解析 → 分块 → 嵌入。

        Returns:
            {"chunks_count": int, "chunks": list[dict]}
        """
        # Step 1: 解析
        parsed: ParsedDocument = DocumentParser.parse(
            content=content,
            file_type=file_type,
            title=title,
            file_name=file_name,
        )

        # Step 2: 分块
        chunks: list[Chunk] = chunk_document(
            content=parsed.content,
            title=parsed.title,
        )

        # Step 3: 嵌入（Demo模式使用伪向量）
        if settings.DEMO_MODE:
            # Demo模式不需要真正嵌入，只存入内存检索器
            retriever = await self._get_retriever()
            if isinstance(retriever, DemoRetriever):
                chunk_dicts = []
                for chunk in chunks:
                    chunk_dicts.append({
                        "id": str(uuid.uuid4()),
                        "content": chunk.content,
                        "document_title": parsed.title,
                        "heading": chunk.heading,
                        "knowledge_base_id": knowledge_base_id,
                        "document_id": document_id,
                    })
                retriever.add_chunks(chunk_dicts)
        else:
            # 生产模式：调用 embedding API
            texts = [chunk.content for chunk in chunks]
            embed_resp = await self.gateway.embed(texts=texts)

            for chunk, embedding in zip(chunks, embed_resp.embeddings):
                chunk.metadata["embedding"] = embedding

            # TODO: 存储到数据库
            logger.info(
                "document_indexed",
                title=parsed.title,
                chunks_count=len(chunks),
            )

        return {
            "title": parsed.title,
            "chunks_count": len(chunks),
            "sections_count": len(parsed.sections),
        }

    async def query(
        self,
        question: str,
        top_k: int = 8,
        knowledge_base_ids: list[str] | None = None,
        user_roles: list[str] | None = None,
    ) -> tuple[list[SearchResult], str]:
        """RAG查询流程：检索 → 上下文组装。

        Returns:
            (search_results, context_text)
        """
        retriever = await self._get_retriever()

        # 检索
        results = await retriever.search(
            query=question,
            top_k=top_k,
            knowledge_base_ids=knowledge_base_ids,
            user_roles=user_roles,
        )

        # 检查是否有足够相关结果
        if not results or (results and results[0].score < MIN_CONTEXT_SCORE):
            logger.info(
                "rag_query_no_relevant_results",
                question=question[:100],
                top_score=results[0].score if results else 0,
            )
            return [], ""

        # 组装上下文
        context = _build_context(results)
        return results, context

    async def chat_with_rag(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
        top_k: int = 8,
        knowledge_base_ids: list[str] | None = None,
        user_roles: list[str] | None = None,
    ) -> tuple[list[SearchResult], str, str]:
        """完整的RAG增强聊天。

        Returns:
            (search_results, system_prompt_with_context, demo_response_text)
        """
        # Step 1: 检索
        results, context = await self.query(
            question=question,
            top_k=top_k,
            knowledge_base_ids=knowledge_base_ids,
            user_roles=user_roles,
        )

        # Step 2: 构建系统提示词
        system_prompt = _RAG_SYSTEM_PROMPT_TEMPLATE.format(context=context) if context else _RAG_SYSTEM_PROMPT_TEMPLATE.format(context="(无相关参考内容，请基于通用保险知识回答，并说明信息未经知识库验证。)")

        return results, system_prompt, ""


async def init_demo_index() -> DemoRetriever:
    """初始化Demo模式的内存索引。"""
    global _demo_retriever
    if _demo_retriever is not None:
        return _demo_retriever

    logger.info("demo_index_initializing")
    _demo_retriever = DemoRetriever()

    # 加载预设知识文档
    demo_docs = get_demo_documents()
    pipeline = RAGPipeline()

    for doc in demo_docs:
        result = await pipeline.index_document(
            content=doc["content"],
            file_type=doc["file_type"],
            title=doc["title"],
            file_name=doc["file_name"],
            knowledge_base_id="demo-kb-001",
            document_id=f"demo-doc-{doc['title'][:4]}",
        )
        logger.info(
            "demo_document_indexed",
            title=doc["title"],
            chunks=result["chunks_count"],
        )

    logger.info(
        "demo_index_ready",
        total_chunks=sum(
            len(_demo_retriever._chunks) for _ in [None]  # just to log
        ),
    )

    return _demo_retriever
