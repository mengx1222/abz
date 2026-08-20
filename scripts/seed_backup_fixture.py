"""Task 38 — 备份演练合成数据 fixture（KB/Document/Chunk(1536-dim vector)/AuditLog）。

用途：backup/restore 云端演练前写入确定性合成业务数据，验证恢复后
Organization / KnowledgeBase / Document / AuditLog / pgvector embedding 仍可读。

安全：仅合成数据，无任何真实客户数据；幂等（已存在同名 KB 则跳过）。
用法：AZB_DATABASE_URL=<asyncpg url> python scripts/seed_backup_fixture.py
"""
import asyncio
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.audit_log import AuditLog
from app.models.knowledge import Document, DocumentChunk, KnowledgeBase
from app.models.organization import Organization
from app.models.user import User

FIXTURE_KB_NAME = "备份演练-合成知识库"
EMBEDDING_DIM = 1536


async def main() -> None:
    url = os.environ["AZB_DATABASE_URL"]
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        existing = (
            await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.name == FIXTURE_KB_NAME)
            )
        ).scalar_one_or_none()
        if existing is not None:
            print("FIXTURE_SKIP already exists (id=%s)" % existing.id)
            await engine.dispose()
            return

        org = (await session.execute(select(Organization))).scalars().first()
        user = (await session.execute(select(User))).scalars().first()
        if org is None or user is None:
            raise RuntimeError("seed 未运行：缺少 Organization/User 基线数据")

        kb = KnowledgeBase(
            id=uuid.uuid4(),
            name=FIXTURE_KB_NAME,
            description="Task 38 backup/restore 演练合成数据",
            category="training",
            status="active",
            is_public=True,
            organization_id=org.id,
            created_by=user.id,
        )
        session.add(kb)
        await session.flush()

        doc = Document(
            id=uuid.uuid4(),
            knowledge_base_id=kb.id,
            title="备份演练文档",
            file_name="backup_fixture.txt",
            file_type="txt",
            file_size=1024,
            content_text="合成内容：安诊保备份恢复演练",
            status="published",
            published_by=user.id,
        )
        session.add(doc)
        await session.flush()

        for i in range(3):
            session.add(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    chunk_index=i,
                    content="备份演练分块 %d" % i,
                    embedding=[0.1] * EMBEDDING_DIM,
                )
            )

        session.add(
            AuditLog(
                user_id=user.id,
                organization_id=org.id,
                action="backup.fixture",
                resource_type="system",
                description="备份演练审计行",
                status="success",
            )
        )
        await session.commit()
        print("FIXTURE_OK kb=%s doc=%s chunks=3 audit=1 dim=%d" % (kb.id, doc.id, EMBEDDING_DIM))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
