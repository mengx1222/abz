#!/usr/bin/env python3
"""E2E 确定性知识 seed —— 供 Playwright E2E 环境使用。

在 alembic upgrade head + scripts/seed.py 之后运行：
  python scripts/e2e_seed_knowledge.py

幂等：检测到同名知识库即跳过（不重复插入）。
数据确定性：
  - 知识库名 / 文档名 / 文本内容全部固定
  - 覆盖 Product QA / Script Generation 检索所需的关键词（医疗险/保障范围/等待期/免赔额/理赔）
  - 附带一个知识库内不存在的产品名（极光量子保险）用于 RAG Refusal 测试
"""
import asyncio
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.knowledge import KnowledgeBase, Document, DocumentChunk

DB_URL = os.environ.get(
    "AZB_DATABASE_URL",
    "postgresql+asyncpg://abz_user:abz_dev_2026@localhost:5432/anzhenbao",
)

KB_NAME = "E2E产品知识库"
DOC_TITLES = ["安诊保百万医疗险产品手册", "安诊保重疾险产品手册"]

# 确定性知识文本（含 E2E 查询关键词）
KB_DOCS = [
    {
        "title": "安诊保百万医疗险产品手册",
        "content": (
            "安诊保百万医疗险保障范围包括：住院医疗费用、门诊手术费用、特殊门诊费用、"
            "住院前后门急诊费用。年度保额最高 600 万元。\n"
            "等待期：90 天（意外医疗无等待期）。\n"
            "免赔额：1 万元（社保报销后剩余部分计入免赔额）。\n"
            "理赔流程：被保险人出院后提交理赔申请，提供发票、诊断证明、费用清单，"
            "保险公司在 10 个工作日内完成审核并赔付。\n"
        ),
    },
    {
        "title": "安诊保重疾险产品手册",
        "content": (
            "安诊保重疾险保障 120 种重大疾病，确诊即赔，一次性给付保额。\n"
            "等待期：180 天。\n"
            "轻症保障：30 种轻症，赔付基本保额的 30%。\n"
            "投保年龄：28 天至 55 周岁。\n"
        ),
    },
]


async def main() -> None:
    engine = create_async_engine(DB_URL, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    # 通过 AI Gateway 生成确定性 embedding（真实 provider 或 mock 均可用）
    from app.ai.gateway import get_ai_gateway

    gateway = get_ai_gateway()

    async with Session() as session:
        # 幂等：已存在则跳过
        existing = (
            await session.execute(select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME))
        ).scalar_one_or_none()
        if existing is not None:
            print(f"e2e_seed_knowledge: KB '{KB_NAME}' exists, skip")
            return

        kb = KnowledgeBase(
            name=KB_NAME,
            description="Playwright E2E 确定性测试知识库（幂等创建）",
            category="product",
            status="active",
            is_public=True,
        )
        session.add(kb)
        await session.flush()

        for doc_spec in KB_DOCS:
            doc = Document(
                knowledge_base_id=kb.id,
                title=doc_spec["title"],
                file_name=f"{doc_spec['title']}.md",
                file_type="md",
                file_size=len(doc_spec["content"]),
                content_text=doc_spec["content"],
                status="published",
                version_number=1,
            )
            session.add(doc)
            await session.flush()

            # 每个文档 1 个 chunk（E2E 足够；检索按全文匹配）
            # embedding 用 AI Gateway 生成（真实 provider 语义向量 / mock 确定性向量）
            embeddings = []
            try:
                resp = await gateway.embed(texts=[doc_spec["content"]])
                embeddings = resp.embeddings
            except Exception as e:
                print(f"e2e_seed_knowledge: embed failed for '{doc_spec['title']}': {e}")

            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                content=doc_spec["content"],
                token_count=len(doc_spec["content"]) // 4,
                search_text=doc_spec["content"],
                embedding=embeddings[0] if embeddings else None,
                metadata_={
                    "heading": "产品保障",
                    "section": "核心条款",
                    "document_title": doc_spec["title"],
                    "knowledge_base_id": str(kb.id),
                },
            )
            session.add(chunk)

        kb.document_count = len(KB_DOCS)
        kb.total_chunks = len(KB_DOCS)

        await session.commit()
        print(f"e2e_seed_knowledge: KB '{KB_NAME}' created ({len(KB_DOCS)} docs)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
