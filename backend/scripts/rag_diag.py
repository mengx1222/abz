"""E2E 诊断：真实 AI 下 RAG 检索是否命中知识库。"""
import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.rag.pipeline import RAGPipeline
from app.models.knowledge import KnowledgeBase, DocumentChunk

DB_URL = os.environ.get(
    "AZB_DATABASE_URL",
    "postgresql+asyncpg://abz_user:abz_dev_2026@localhost:5432/anzhenbao",
)


async def main():
    engine = create_async_engine(DB_URL, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        kbs = (await session.execute(select(KnowledgeBase.name))).scalars().all()
        chunks = (await session.execute(select(DocumentChunk.id, DocumentChunk.content).limit(5))).all()
        print("KBs:", list(kbs))
        print("chunks:", len(chunks))

        pipeline = RAGPipeline(db=session)
        for q in ["介绍一下医疗险的保障范围和等待期", "安诊保百万医疗险的理赔流程是什么", "极光量子保险的承保范围是什么"]:
            results, ctx = await pipeline.query(question=q, top_k=5)
            print(f"\nQ: {q}")
            print(f"  results={len(results)} ctx_len={len(ctx)}")
            for r in results[:3]:
                print(f"  score={r.score:.3f} title={r.document_title[:24]!r} content={r.content[:36]!r}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
