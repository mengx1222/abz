#!/usr/bin/env python3
"""E2E 确定性知识 seed —— 供 Playwright E2E 环境使用。

在 alembic upgrade head + scripts/seed.py 之后运行：
  python scripts/e2e_seed_knowledge.py

幂等：检测到同名知识库即跳过（不重复插入）；对计数不一致的半成品状态打印警告
（不静默、不自动重建，避免破坏其他测试对数据的假设）。

Task 24 (P2-4) 改动：
- DB_URL 从 app.core.config.settings 读取（此前默认值硬编码开发库凭据）
- embedding 失败 fail-fast（抛 RuntimeError），杜绝 NULL 向量 chunk 静默污染
  pgvector 检索（此前 embed 异常时 chunk.embedding=None 照常入库）
- 核心逻辑抽为 seed_e2e_knowledge(session)，供 backend-pg 幂等性测试直接调用

数据确定性：
  - 知识库名 / 文档名 / 文本内容全部固定
  - 覆盖 Product QA / Script Generation 检索所需的关键词（医疗险/保障范围/等待期/免赔额/理赔）
  - 附带一个知识库内不存在的产品名（极光量子保险）用于 RAG Refusal 测试
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk

# Task 24: 统一从 settings 读取（AZB_DATABASE_URL），不再硬编码 dev 凭据
DB_URL = settings.DATABASE_URL

KB_NAME = "E2E产品知识库"
DOC_TITLES = [
    "安诊保百万医疗险产品手册", "安诊保重疾险产品手册",
    "安诊保销售合规与常见异议指南",
]

# 确定性知识文本（含 E2E 查询关键词 + product_type 用于 RAG 产品边界测试）
# 每个产品拆分为 ≥3 个 chunk：产品边界过滤后仍达到 Confidence Gate（HIGH 需 count>=3）
# RDY 阶段1：新增第 3 个文档「销售合规与常见异议指南」（product_type=通用销售话术，
# 不被医疗险/重疾险 product_type 精确过滤召回；Agent 自由召回场景可命中异议/合规依据）。
# 数据标识：KB.metadata_["dataset_tag"]="E2E_TEST/PILOT"，chunk metadata 同步携带，
# 与 DEMO（demo_mode 用户）区分，供 Pilot 数据审计追溯。
KB_DOCS = [
    {
        "title": "安诊保百万医疗险产品手册",
        "product_type": "医疗险",
        "chunks": [
            "安诊保百万医疗险保障范围包括：住院医疗费用、门诊手术费用、特殊门诊费用、"
            "住院前后门急诊费用。年度保额最高 600 万元。",
            "等待期：90 天（意外医疗无等待期）。免赔额：1 万元（社保报销后剩余部分计入免赔额）。",
            "理赔流程：被保险人出院后提交理赔申请，提供发票、诊断证明、费用清单，"
            "保险公司在 10 个工作日内完成审核并赔付。",
        ],
    },
    {
        "title": "安诊保重疾险产品手册",
        "product_type": "重疾险",
        "chunks": [
            "安诊保重疾险保障 120 种重大疾病，确诊即赔，一次性给付保额。",
            "等待期：180 天。轻症保障：30 种轻症，赔付基本保额的 30%。",
            "投保年龄：28 天至 55 周岁。保费与投保年龄、保额相关。",
        ],
    },
    {
        "title": "安诊保销售合规与常见异议指南",
        "product_type": "通用销售话术",
        "chunks": [
            "常见异议应对：客户质疑保费贵时，可从保障范围与理赔服务切入，说明费率与"
            "保障责任对应关系，不夸大收益；客户质疑理赔难时，引用理赔时效条款（审核 10 个工作日）"
            "并建议保留发票与诊断证明。",
            "合规红线：销售过程中严禁向客户承诺保本保收益、严禁返佣或变相返佣、严禁代客户"
            "签字或代操作投保；违反红线须立即停止沟通并按公司合规流程上报。",
            "高风险客户识别：客户提出返佣、承诺收益、私下打款等要求时，判定为合规高风险，"
            "应拒绝不合理要求、记录沟通内容并上报合规专员。",
        ],
    },
]


def _expected_counts() -> tuple[int, int]:
    """期望的文档数 / chunk 总数（幂等校验基线）。"""
    return len(KB_DOCS), sum(len(d["chunks"]) for d in KB_DOCS)


async def seed_e2e_knowledge(session: AsyncSession) -> bool:
    """幂等创建 E2E 确定性知识库。

    返回 True=本次新建；False=已存在（跳过，含计数不一致警告）。

    注意：本函数只做 add/flush，不 commit —— 由调用方（main 或测试）控制事务，
    以便测试验证失败时无半成品残留（rollback 语义）。
    """
    from app.ai.gateway import get_ai_gateway

    gateway = get_ai_gateway()

    expected_docs, expected_chunks = _expected_counts()

    # 幂等：已存在则跳过（计数不一致 → 警告，不静默）
    existing = (
        await session.execute(select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME))
    ).scalar_one_or_none()
    if existing is not None:
        if (
            existing.document_count != expected_docs
            or existing.total_chunks != expected_chunks
        ):
            print(
                f"e2e_seed_knowledge: WARN KB '{KB_NAME}' exists with mismatched counts "
                f"(docs={existing.document_count}/{expected_docs}, "
                f"chunks={existing.total_chunks}/{expected_chunks}); skip (idempotent)"
            )
        else:
            print(f"e2e_seed_knowledge: KB '{KB_NAME}' exists, skip")
        return False

    kb = KnowledgeBase(
        name=KB_NAME,
        description="Playwright E2E 确定性测试知识库（幂等创建）",
        category="product",
        status="active",
        is_public=True,
        # RDY 阶段1：稳定数据标识 —— 该 KB 同时服务 E2E 测试与 Internal Pilot 演示，
        # metadata_["dataset_tag"] 与 DEMO 数据区分（无真实业务文档/客户信息）
        metadata_={"dataset_tag": "E2E_TEST/PILOT"},
    )
    session.add(kb)
    await session.flush()

    for doc_spec in KB_DOCS:
        chunks_text = doc_spec["chunks"]
        full_content = "\n".join(chunks_text)
        doc = Document(
            knowledge_base_id=kb.id,
            title=doc_spec["title"],
            file_name=f"{doc_spec['title']}.md",
            file_type="md",
            file_size=len(full_content),
            content_text=full_content,
            status="published",
            version_number=1,
        )
        session.add(doc)
        await session.flush()

        # 每个文档 ≥3 个 chunk（产品边界过滤后仍需满足 Confidence Gate HIGH: count>=3）
        # Task 24: embedding 失败 → fail-fast（此前静默容忍 None 向量入库污染检索）
        try:
            resp = await gateway.embed(texts=chunks_text)
        except Exception as e:
            raise RuntimeError(
                f"e2e_seed_knowledge: embedding failed for '{doc_spec['title']}': {e}"
            ) from e
        if len(resp.embeddings) < len(chunks_text):
            raise RuntimeError(
                f"e2e_seed_knowledge: embedding count mismatch for '{doc_spec['title']}' "
                f"(got {len(resp.embeddings)}, need {len(chunks_text)})"
            )

        for idx, chunk_text in enumerate(chunks_text):
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_text,
                token_count=len(chunk_text) // 4,
                search_text=chunk_text,
                embedding=resp.embeddings[idx],
                metadata_={
                    "heading": "产品保障",
                    "section": "核心条款",
                    "document_title": doc_spec["title"],
                    "knowledge_base_id": str(kb.id),
                    "product_type": doc_spec["product_type"],
                    "dataset_tag": "E2E_TEST/PILOT",
                },
            )
            session.add(chunk)

    kb.document_count = expected_docs
    kb.total_chunks = expected_chunks
    return True


async def main() -> None:
    engine = create_async_engine(DB_URL, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        created = await seed_e2e_knowledge(session)
        await session.commit()
        if created:
            _, expected_chunks = _expected_counts()
            print(
                f"e2e_seed_knowledge: KB '{KB_NAME}' created "
                f"({len(KB_DOCS)} docs, {expected_chunks} chunks)"
            )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
