"""Task 38 — 恢复后数据库验证脚本（云端 restore 演练用，真实 PostgreSQL + pgvector）。

用法:
  # 备份前基线快照（workflow 保存 JSON）
  python scripts/verify_restored_db.py --db-url <asyncpg-url> --out baseline.json

  # 恢复后对比（不匹配则退出非 0，阻止 CI 通过）
  python scripts/verify_restored_db.py --db-url <asyncpg-url> --baseline baseline.json

验证维度（阶段 4/7）:
  - 关键表数量（users/roles/role_permissions/organizations/knowledge_bases/
    documents/document_chunks/audit_logs/training_scenarios）
  - alembic_version（迁移状态一致）
  - pgvector：document_chunks.embedding 非空计数 + vector 维度
"""
import argparse
import asyncio
import json
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

KEY_TABLES = [
    "users", "roles", "role_permissions", "organizations",
    "knowledge_bases", "documents", "document_chunks",
    "audit_logs", "training_scenarios",
]


async def snapshot(db_url: str) -> dict:
    eng = create_async_engine(db_url)
    counts: dict = {}
    try:
        async with eng.connect() as conn:
            for t in KEY_TABLES:
                try:
                    r = await conn.execute(text('SELECT count(*) FROM "%s"' % t))
                    counts[t] = r.scalar_one()
                except Exception:
                    counts[t] = None
            try:
                r = await conn.execute(text("SELECT version_num FROM alembic_version"))
                counts["alembic_version"] = r.scalar_one()
            except Exception:
                counts["alembic_version"] = None
            try:
                r = await conn.execute(
                    text("SELECT count(*) FROM document_chunks WHERE embedding IS NOT NULL")
                )
                counts["chunks_with_embedding"] = r.scalar_one()
                r = await conn.execute(
                    text("SELECT vector_dims(embedding) FROM document_chunks "
                         "WHERE embedding IS NOT NULL LIMIT 1")
                )
                counts["embedding_dims"] = r.scalar_one() if r.rowcount else None
            except Exception:
                counts["chunks_with_embedding"] = -1
                counts["embedding_dims"] = None
    finally:
        await eng.dispose()
    return counts


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-url", required=True, help="asyncpg URL（验证目标库）")
    ap.add_argument("--out", help="快照输出 JSON 路径（baseline 模式）")
    ap.add_argument("--baseline", help="基线 JSON 路径（verify 模式）")
    a = ap.parse_args()

    snap = await snapshot(a.db_url)

    if a.baseline:
        with open(a.baseline, encoding="utf-8") as f:
            base = json.load(f)
        keys = set(base) | set(snap)
        mismatches = {
            k: {"baseline": base.get(k), "restored": snap.get(k)}
            for k in keys
            if base.get(k) != snap.get(k)
        }
        print(json.dumps(
            {"mode": "verify", "baseline": base, "restored": snap, "mismatches": mismatches},
            ensure_ascii=False,
        ))
        if mismatches:
            print("VERIFY_FAILED " + json.dumps(mismatches), file=sys.stderr)
            sys.exit(1)
        print("VERIFY_OK restored data matches baseline")
    else:
        print(json.dumps({"mode": "snapshot", "snapshot": snap}, ensure_ascii=False))
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                json.dump(snap, f, ensure_ascii=False)
        print("SNAPSHOT_OK")


if __name__ == "__main__":
    asyncio.run(main())
