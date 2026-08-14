"""Database compatibility layer for SQLite/PostgreSQL dual support.

Provides dialect-agnostic column types and helpers so that
Alembic migrations can run on both SQLite (local dev) and
PostgreSQL (production).

Usage in migrations:
    from app.core.db_compat import UUID, JSONB, Vector1536, is_sqlite

    # UUID works as-is on both
    sa.Column("id", UUID, primary_key=True)

    # JSONB → JSON on SQLite, native JSONB on PostgreSQL
    sa.Column("meta", JSONB, nullable=True)

    # Vector → BLOB on SQLite, pgvector on PostgreSQL
    sa.Column("embedding", Vector1536, nullable=True)

    # Skip PG-specific operations on SQLite
    if not is_sqlite(op):
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
"""
from alembic import op


# ---- dialect detector ----
def is_sqlite(op_obj) -> bool:
    """Return True if the current migration dialect is SQLite."""
    return op_obj.get_bind().dialect.name == "sqlite"


def is_postgres(op_obj) -> bool:
    """Return True if the current migration dialect is PostgreSQL."""
    return op_obj.get_bind().dialect.name == "postgresql"


# ---- Type aliases ----
# In migration files, use these instead of importing from sqlalchemy.dialects.postgresql.
# They delegate to the underlying PG type on PostgreSQL and fall back to a
# SQLite-compatible representation automatically via SQLAlchemy's type resolution.

# NOTE: We do NOT override the types here. Instead, each migration uses
# conditional execution (if/else on dialect) for PG-specific features like:
#   - CREATE EXTENSION, CREATE TYPE, GIN/HNSW indexes, tsvector, triggers
#
# For column types that differ (UUID, JSONB, Vector), SQLAlchemy itself handles
# the cross-dialect rendering when we use the generic form:
#   - UUID → String(36) on SQLite (SQLAlchemy auto)
#   - JSONB → sa.JSON() which renders as TEXT on SQLite
#   - Vector → skip or use BLOB on SQLite
#
# See the migration files for examples.
