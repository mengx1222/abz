#!/usr/bin/env python3
"""Phase 7 — PostgreSQL + pgvector 生产环境验证脚本。

验证项目在真实 PostgreSQL + pgvector 环境下的完整功能：
  1. 基础设施预检（PostgreSQL, pgvector, Redis）
  2. Alembic 迁移验证（表数量、关键表、列、外键、索引）
  3. 种子数据验证（用户、角色）
  4. API 烟雾测试（health, ready, login）
  5. 生产模式专项测试（AI provider, DB 查询, pgvector）

用法:
    cd backend && python scripts/phase7_pg_verify.py
    cd backend && python scripts/phase7_pg_verify.py --db-url "postgresql+asyncpg://..."
    cd backend && python scripts/phase7_pg_verify.py --skip-api-test
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# 确保项目根目录在 sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# ============================================================
# 颜色工具
# ============================================================

class _C:
    """ANSI 颜色码。"""
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    DIM    = "\033[2m"


def _pass(msg: str) -> None:
    print(f"  {_C.GREEN}{_C.BOLD}PASS{_C.RESET}  {msg}")


def _fail(msg: str) -> None:
    print(f"  {_C.RED}{_C.BOLD}FAIL{_C.RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_C.YELLOW}{_C.BOLD}WARN{_C.RESET}  {msg}")


def _section(title: str) -> None:
    print(f"\n{_C.BOLD}{_C.CYAN}{'=' * 60}{_C.RESET}")
    print(f"{_C.BOLD}{_C.CYAN}  {title}{_C.RESET}")
    print(f"{_C.BOLD}{_C.CYAN}{'=' * 60}{_C.RESET}")


# ============================================================
# 结果追踪
# ============================================================

class _Results:
    """跟踪所有检查结果。"""
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def ok(self, msg: str) -> None:
        self.passed.append(msg)
        _pass(msg)

    def bad(self, msg: str) -> None:
        self.failed.append(msg)
        _fail(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        _warn(msg)

    def summary(self) -> None:
        print(f"\n{_C.BOLD}{'=' * 60}{_C.RESET}")
        print(f"{_C.BOLD}  验证总结{_C.RESET}")
        print(f"{_C.BOLD}{'=' * 60}{_C.RESET}")
        print(f"  {_C.GREEN}PASS: {len(self.passed)}{_C.RESET}")
        if self.warnings:
            print(f"  {_C.YELLOW}WARN: {len(self.warnings)}{_C.RESET}")
        if self.failed:
            print(f"  {_C.RED}FAIL: {len(self.failed)}{_C.RESET}")
            for f in self.failed:
                print(f"    {_C.RED}✗ {f}{_C.RESET}")
        print()
        if not self.failed:
            print(f"  {_C.GREEN}{_C.BOLD}✓ 所有检查通过！{self.RESET}")
        else:
            print(f"  {_C.RED}{_C.BOLD}✗ 存在失败的检查项，请修复后重试。{_C.RESET}")
        print()


R = _Results()

# ============================================================
# 默认配置
# ============================================================

DEFAULT_DB_URL = (
    "postgresql+asyncpg://abz_user:abz_dev_2026@localhost:5432/anzhenbao"
)
DEFAULT_SYNC_DB_URL = (
    "postgresql://abz_user:abz_dev_2026@localhost:5432/anzhenbao"
)
API_PORT = 8190  # 使用非标准端口避免冲突

# ============================================================
# 期望的表（30 个）
# ============================================================

EXPECTED_TABLES = {
    # 0001_initial
    "roles", "permissions", "role_permissions", "organizations", "users",
    # 0002_knowledge_ai
    "knowledge_bases", "documents", "document_chunks", "ai_request_logs", "ai_feedbacks",
    # 0003_scripts
    "scripts", "script_versions", "script_favorites",
    # 0004_community
    "community_posts", "community_post_comments", "community_post_likes", "community_post_favorites",
    # 0005_remaining
    "customer_tags", "customers", "customer_interactions", "customer_followups",
    "training_scenarios", "training_sessions", "training_messages", "training_scores",
    "conversations", "messages",
    # 0006_notification_growth_audit
    "notifications", "notification_preferences", "user_achievements", "audit_logs",
}

# 关键表（必须存在）
CRITICAL_TABLES = {
    "users", "roles", "organizations", "permissions",
    "customers", "customer_interactions", "customer_followups",
    "knowledge_bases", "documents", "document_chunks",
    "community_posts", "community_post_comments",
    "scripts", "training_scenarios", "training_sessions",
    "notifications", "notification_preferences",
    "audit_logs", "ai_request_logs", "ai_feedbacks",
}

# 关键列检查（表名 → 期望的列列表）
EXPECTED_COLUMNS: dict[str, list[str]] = {
    "users": ["id", "phone", "name", "hashed_password", "role_id", "organization_id", "is_active"],
    "roles": ["id", "code", "name", "description", "level"],
    "organizations": ["id", "name", "type", "is_active"],
    "customers": ["id", "name", "phone", "customer_type", "current_stage",
                   "intention_level", "assigned_to", "organization_id", "is_deleted"],
    "knowledge_bases": ["id", "name", "description", "is_active", "effective_date", "expiry_date"],
    "documents": ["id", "knowledge_base_id", "title", "file_path", "status",
                  "version_number", "effective_date", "expiry_date"],
    "document_chunks": ["id", "document_id", "content", "embedding", "chunk_index"],
    "community_posts": ["id", "title", "content", "category", "author_id", "is_deleted"],
    "training_sessions": ["id", "user_id", "scenario_id", "status", "started_at"],
    "notifications": ["id", "user_id", "type", "title", "content", "is_read"],
    "audit_logs": ["id", "user_id", "action", "resource_type", "request_id"],
}

# 期望的外键关系
EXPECTED_FKS: list[tuple[str, str, str]] = [
    # (constraint_name_pattern, from_table, to_table)
    ("users_role_id", "users", "roles"),
    ("users_organization_id", "users", "organizations"),
    ("customers_assigned_to", "customers", "users"),
    ("customers_organization_id", "customers", "organizations"),
    ("documents_knowledge_base_id", "documents", "knowledge_bases"),
    ("document_chunks_document_id", "document_chunks", "documents"),
    ("training_sessions_user_id", "training_sessions", "users"),
    ("training_sessions_scenario_id", "training_sessions", "training_scenarios"),
    ("notifications_user_id", "notifications", "users"),
]

# 期望的索引（至少这些列应该有索引）
EXPECTED_INDEXES: list[tuple[str, str]] = [
    # (table, column_pattern)
    ("users", "phone"),
    ("customers", "organization_id"),
    ("customers", "assigned_to"),
    ("documents", "knowledge_base_id"),
    ("document_chunks", "document_id"),
    ("community_posts", "author_id"),
    ("notifications", "user_id"),
    ("training_sessions", "user_id"),
]


# ============================================================
# 辅助函数
# ============================================================

def _run_shell(cmd: str, timeout: int = 10) -> tuple[int, str, str]:
    """运行 shell 命令，返回 (exit_code, stdout, stderr)。"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def _get_sync_db_url(async_url: str) -> str:
    """将 asyncpg URL 转为 psycopg2 同步 URL。"""
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


def _get_psycopg2_dsn(async_url: str) -> dict:
    """从 async URL 解析出 psycopg2 连接参数。"""
    sync = _get_sync_db_url(async_url)
    # postgresql://user:pass@host:port/dbname
    without_prefix = sync.replace("postgresql://", "")
    if "/" in without_prefix:
        auth_host, dbname = without_prefix.rsplit("/", 1)
    else:
        auth_host = without_prefix
        dbname = "anzhenbao"
    if "@" in auth_host:
        user_pass, host_port = auth_host.rsplit("@", 1)
        if ":" in user_pass:
            user, password = user_pass.split(":", 1)
        else:
            user, password = user_pass, ""
    else:
        user, password = "", ""
    if ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host, port = host_port, "5432"
    return {
        "host": host, "port": int(port), "dbname": dbname,
        "user": user, "password": password,
    }


def _query_sync(db_url: str, sql: str) -> list[dict]:
    """使用 psycopg2 执行同步查询，返回行列表。"""
    import psycopg2  # type: ignore
    dsn = _get_psycopg2_dsn(db_url)
    conn = psycopg2.connect(**dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
            return []
    finally:
        conn.close()


def _query_sync_value(db_url: str, sql: str) -> str | None:
    """执行同步查询，返回第一行第一列的值。"""
    rows = _query_sync(db_url, sql)
    if rows:
        return str(list(rows[0].values())[0])
    return None


# ============================================================
# Phase 1: 基础设施预检
# ============================================================

def check_infrastructure() -> None:
    """检查 PostgreSQL, pgvector, Redis 是否就绪。"""
    _section("Phase 1: 基础设施预检")

    # --- PostgreSQL ---
    print(f"\n  检查 PostgreSQL...")
    code, out, err = _run_shell("pg_isready -h localhost -p 5432 -t 5")
    if code == 0:
        R.ok("PostgreSQL 正在运行 (pg_isready)")
    else:
        # 尝试直接连接
        code2, _, _ = _run_shell(
            f"psql {_get_sync_db_url(DEFAULT_DB_URL)} -c 'SELECT 1' -t 2>&1"
        )
        if code2 == 0:
            R.ok("PostgreSQL 可连接 (psql 验证)")
        else:
            R.bad(f"PostgreSQL 不可用 (pg_isready: {out or err})")

    # --- pgvector ---
    print(f"\n  检查 pgvector 扩展...")
    try:
        result = _query_sync(
            DEFAULT_DB_URL,
            "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname FROM pg_extension WHERE extname = 'vector';",
        )
        if result and any(r.get("extname") == "vector" for r in result):
            R.ok("pgvector 扩展已安装并启用")
        else:
            R.bad("pgvector 扩展未能启用")
    except Exception as e:
        # 尝试用 psql
        code, out, err = _run_shell(
            f"psql {_get_sync_db_url(DEFAULT_DB_URL)} -c \"CREATE EXTENSION IF NOT EXISTS vector;\" -t 2>&1",
        )
        if code == 0:
            R.ok(f"pgvector 扩展已安装 (psql 验证)")
        else:
            R.bad(f"pgvector 扩展不可用: {err or out}")

    # --- Redis ---
    print(f"\n  检查 Redis...")
    code, out, err = _run_shell("redis-cli -h localhost -p 6379 ping", timeout=5)
    if "PONG" in (out or "").upper():
        R.ok("Redis 正在运行 (redis-cli PING → PONG)")
    else:
        # 尝试 python
        try:
            import redis as redis_lib
            r = redis_lib.Redis(host="localhost", port=6379, socket_timeout=3)
            if r.ping():
                R.ok("Redis 正在运行 (python-redis 验证)")
            else:
                R.bad("Redis 连接失败 (python-redis)")
        except Exception:
            R.bad(f"Redis 不可用 (redis-cli: {out or err})")


# ============================================================
# Phase 2: 迁移验证
# ============================================================

def check_migrations(db_url: str) -> None:
    """运行 alembic upgrade head 并验证表。"""
    _section("Phase 2: Alembic 迁移验证")

    # --- Run alembic upgrade head ---
    print(f"\n  运行 alembic upgrade head...")
    env = os.environ.copy()
    env["AZB_DATABASE_URL"] = db_url
    env["AZB_DEMO_MODE"] = "false"
    code, out, err = _run_shell(
        f"cd {_BACKEND_DIR} && python -m alembic upgrade head 2>&1",
        timeout=30,
    )
    combined = (out + "\n" + err).strip()
    if code == 0 or "already at head" in combined.lower() or "running upgrade" in combined.lower():
        R.ok("alembic upgrade head 执行成功")
    else:
        R.warn(f"alembic upgrade head 返回非零: {combined[:200]}")

    # --- List all tables ---
    print(f"\n  查询数据库表...")
    try:
        tables_result = _query_sync(
            db_url,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name;",
        )
        actual_tables = {r["table_name"] for r in tables_result} if tables_result else set()
        print(f"  实际表数量: {len(actual_tables)}")

        if len(actual_tables) >= 30:
            R.ok(f"表数量 >= 30 (实际: {len(actual_tables)})")
        else:
            R.bad(f"表数量 < 30 (实际: {len(actual_tables)})")

        # --- Check expected tables ---
        print(f"\n  检查关键表...")
        for t in sorted(CRITICAL_TABLES):
            if t in actual_tables:
                R.ok(f"表 '{t}' 存在")
            else:
                R.bad(f"表 '{t}' 缺失")

        # --- Check for unexpected missing tables ---
        missing = EXPECTED_TABLES - actual_tables
        if missing:
            print(f"\n  {_C.YELLOW}缺少的期望表 ({len(missing)}):{_C.RESET}")
            for t in sorted(missing):
                R.bad(f"缺少表 '{t}'")
        else:
            R.ok("所有 30 个期望表均存在")

        # --- Extra tables (alembic_version is expected) ---
        extra = actual_tables - EXPECTED_TABLES - {"alembic_version"}
        if extra:
            R.warn(f"额外的表: {sorted(extra)}")

        return actual_tables

    except Exception as e:
        R.bad(f"查询 information_schema.tables 失败: {e}")
        return set()


# ============================================================
# Phase 3: 数据完整性
# ============================================================

def check_data_integrity(db_url: str) -> None:
    """检查列、外键、索引。"""
    _section("Phase 3: 数据完整性")

    # --- Columns ---
    print(f"\n  检查关键列...")
    try:
        cols_result = _query_sync(
            db_url,
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' ORDER BY table_name, column_name;",
        )
        if cols_result is None:
            R.bad("无法查询 information_schema.columns")
            return

        # 构建 table → set(columns) 映射
        table_columns: dict[str, set[str]] = {}
        for r in cols_result:
            table_columns.setdefault(r["table_name"], set()).add(r["column_name"])

        for table, expected_cols in EXPECTED_COLUMNS.items():
            actual = table_columns.get(table, set())
            missing_cols = set(expected_cols) - actual
            if missing_cols:
                R.bad(f"表 '{table}' 缺少列: {sorted(missing_cols)}")
            else:
                R.ok(f"表 '{table}' 所有关键列存在 ({len(expected_cols)} 列)")

    except Exception as e:
        R.bad(f"列检查失败: {e}")

    # --- Foreign Keys ---
    print(f"\n  检查外键关系...")
    try:
        fk_result = _query_sync(
            db_url,
            "SELECT tc.constraint_name, tc.table_name, ccu.table_name AS foreign_table_name "
            "FROM information_schema.table_constraints AS tc "
            "JOIN information_schema.referential_constraints AS rc "
            "  ON tc.constraint_name = rc.constraint_name "
            "JOIN information_schema.constraint_column_usage AS ccu "
            "  ON rc.unique_constraint_name = ccu.constraint_name "
            "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public' "
            "ORDER BY tc.table_name;",
        )
        if fk_result:
            # 构建 (from_table, to_table) → constraint_name 映射
            fk_map: dict[tuple[str, str], str] = {}
            for r in fk_result:
                key = (r["table_name"], r["foreign_table_name"])
                fk_map[key] = r["constraint_name"]

            for _, from_table, to_table in EXPECTED_FKS:
                if (from_table, to_table) in fk_map:
                    R.ok(f"外键 {from_table} → {to_table} 存在")
                else:
                    R.bad(f"外键 {from_table} → {to_table} 缺失")
        else:
            R.warn("未找到任何外键关系")

    except Exception as e:
        R.bad(f"外键检查失败: {e}")

    # --- Indexes ---
    print(f"\n  检查关键索引...")
    try:
        idx_result = _query_sync(
            db_url,
            "SELECT tablename, indexname FROM pg_indexes "
            "WHERE schemaname = 'public' ORDER BY tablename, indexname;",
        )
        if idx_result:
            # 构建 table → list[indexname]
            table_indexes: dict[str, list[str]] = {}
            for r in idx_result:
                table_indexes.setdefault(r["tablename"], []).append(r["indexname"])

            for table, col_pattern in EXPECTED_INDEXES:
                indexes = table_indexes.get(table, [])
                found = any(col_pattern in idx for idx in indexes)
                if found:
                    R.ok(f"表 '{table}' 列 '{col_pattern}' 有索引")
                else:
                    R.warn(f"表 '{table}' 列 '{col_pattern}' 未找到索引")
        else:
            R.warn("未找到任何索引")

    except Exception as e:
        R.bad(f"索引检查失败: {e}")


# ============================================================
# Phase 4: 种子数据验证
# ============================================================

def check_seed_data(db_url: str) -> None:
    """检查种子数据是否存在。"""
    _section("Phase 4: 种子数据验证")

    print(f"\n  检查各表数据量...")
    checks = [
        ("users", 1, "用户数据"),
        ("roles", 1, "角色数据"),
        ("permissions", 1, "权限数据"),
        ("organizations", 1, "组织数据"),
    ]

    for table, min_count, label in checks:
        try:
            val = _query_sync_value(db_url, f"SELECT COUNT(*) FROM {table};")
            count = int(val) if val else 0
            if count >= min_count:
                R.ok(f"表 '{table}' 有 {count} 行 ({label})")
            else:
                R.warn(f"表 '{table}' 仅有 {count} 行，期望 >= {min_count} ({label})")
                R.warn(f"  提示: 运行 `cd backend && python -m scripts.seed` 插入种子数据")
        except Exception as e:
            R.warn(f"无法查询表 '{table}': {e}")

    # 检查 knowledge_bases（可选，可能为空）
    try:
        val = _query_sync_value(db_url, "SELECT COUNT(*) FROM knowledge_bases;")
        count = int(val) if val else 0
        if count > 0:
            R.ok(f"表 'knowledge_bases' 有 {count} 行")
        else:
            R.warn(f"表 'knowledge_bases' 为空 — RAG 功能需要知识库数据")
    except Exception:
        pass


# ============================================================
# Phase 5: API 烟雾测试
# ============================================================

def check_api_smoke(db_url: str, skip: bool = False) -> None:
    """启动后端服务并测试 API。"""
    _section("Phase 5: API 烟雾测试")

    if skip:
        _warn("--skip-api-test 已设置，跳过 API 测试")
        return

    import urllib.request
    import urllib.error

    base_url = f"http://127.0.0.1:{API_PORT}"
    proc = None

    # --- Start backend ---
    print(f"\n  启动后端服务 (端口 {API_PORT})...")
    env = os.environ.copy()
    env["AZB_DEMO_MODE"] = "false"
    env["AZB_DATABASE_URL"] = db_url
    env["AZB_DEBUG"] = "false"
    env["AZB_APP_ENV"] = "production"
    env["AZB_AI_PROVIDER"] = "deepseek"
    env["AZB_AI_API_KEY"] = "sk-test-key-for-verification"
    env["AZB_AI_BASE_URL"] = "https://api.deepseek.com"
    env["AZB_AI_MODEL"] = "deepseek-chat"

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "0.0.0.0", "--port", str(API_PORT)],
            cwd=str(_BACKEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        # 等待服务启动
        print(f"  等待服务启动...")
        max_wait = 15
        for i in range(max_wait * 2):
            time.sleep(0.5)
            try:
                req = urllib.request.Request(f"{base_url}/api/v1/health")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        print(f"  服务已启动 ({(i + 1) * 0.5:.1f}s)")
                        break
            except Exception:
                continue
        else:
            # 读取进程输出帮助调试
            if proc and proc.stdout:
                output = proc.stdout.read(2000).decode(errors="replace")
                R.bad(f"后端服务在 {max_wait}s 内未启动")
                print(f"  {_C.DIM}进程输出: {output[:500]}{_C.RESET}")
            return

        # --- Test /api/v1/health ---
        print(f"\n  测试 GET /api/v1/health...")
        try:
            req = urllib.request.Request(f"{base_url}/api/v1/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if resp.status == 200 and data.get("data", {}).get("status") == "healthy":
                    R.ok("/api/v1/health → 200, status=healthy")
                else:
                    R.bad(f"/api/v1/health 返回异常: {data}")
        except Exception as e:
            R.bad(f"/api/v1/health 请求失败: {e}")

        # --- Test /api/v1/ready ---
        print(f"\n  测试 GET /api/v1/ready...")
        try:
            req = urllib.request.Request(f"{base_url}/api/v1/ready")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                checks_data = data.get("data", {}).get("checks", {})
                status = data.get("data", {}).get("status", "")
                db_check = checks_data.get("database", "")

                if status == "ready":
                    R.ok(f"/api/v1/ready → 200, status=ready")
                else:
                    R.warn(f"/api/v1/ready → status={status} (database={db_check})")

                if db_check == "connected":
                    R.ok(f"  checks.database = 'connected'")
                elif db_check == "not_required":
                    R.warn(f"  checks.database = 'not_required' (可能仍在 DEMO_MODE)")
                else:
                    R.bad(f"  checks.database = '{db_check}'")

                ai_check = checks_data.get("ai_provider", "")
                if ai_check in ("configured", "mock_ready"):
                    R.ok(f"  checks.ai_provider = '{ai_check}'")
                else:
                    R.warn(f"  checks.ai_provider = '{ai_check}'")

        except Exception as e:
            R.bad(f"/api/v1/ready 请求失败: {e}")

        # --- Test /api/v1/auth/login ---
        print(f"\n  测试 POST /api/v1/auth/login...")
        try:
            # 尝试使用种子数据的用户登录
            login_payload = json.dumps({
                "phone": "13800138000",
                "password": "admin123456",
            }).encode()
            req = urllib.request.Request(
                f"{base_url}/api/v1/auth/login",
                data=login_payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                token_data = data.get("data", {})
                if token_data.get("access_token"):
                    R.ok(f"/api/v1/auth/login → 200, access_token 获取成功")
                else:
                    R.warn(f"/api/v1/auth/login → 200 但未返回 token: {data}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code == 401:
                R.warn(f"/api/v1/auth/login → 401 (种子用户可能未创建或密码不匹配)")
                R.warn(f"  提示: 运行 `cd backend && python -m scripts.seed` 创建种子用户")
            else:
                R.bad(f"/api/v1/auth/login → {e.code}: {body[:200]}")
        except Exception as e:
            R.bad(f"/api/v1/auth/login 请求失败: {e}")

    except Exception as e:
        R.bad(f"API 测试异常: {e}")

    finally:
        # --- Stop backend ---
        if proc is not None:
            print(f"\n  停止后端服务...")
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                proc.wait(timeout=5)
                R.ok("后端服务已停止")
            except Exception:
                proc.kill()
                R.ok("后端服务已强制停止")


# ============================================================
# Phase 6: 生产模式专项测试
# ============================================================

def check_production_mode(db_url: str) -> None:
    """验证生产模式下的特定行为。"""
    _section("Phase 6: 生产模式专项测试")

    # --- effective_ai_provider ---
    print(f"\n  检查 effective_ai_provider...")
    env = os.environ.copy()
    env["AZB_DEMO_MODE"] = "false"
    env["AZB_AI_PROVIDER"] = "deepseek"
    env["AZB_DATABASE_URL"] = db_url

    try:
        # 需要临时设置环境变量再导入 settings
        # 先清除可能已缓存的 settings
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("app.core.config"):
                del sys.modules[mod_name]

        os.environ["AZB_DEMO_MODE"] = "false"
        os.environ["AZB_AI_PROVIDER"] = "deepseek"
        os.environ["AZB_DATABASE_URL"] = db_url

        from app.core.config import Settings
        s = Settings()
        provider = s.effective_ai_provider
        if provider == "mock":
            R.bad(f"effective_ai_provider = 'mock' (应返回配置的 provider)")
        else:
            R.ok(f"effective_ai_provider = '{provider}' (非 mock)")
    except Exception as e:
        R.bad(f"检查 effective_ai_provider 失败: {e}")
    finally:
        # 恢复环境
        os.environ.pop("AZB_DEMO_MODE", None)
        os.environ.pop("AZB_AI_PROVIDER", None)
        os.environ.pop("AZB_DATABASE_URL", None)

    # --- DB session actual query ---
    print(f"\n  测试 DB 实际查询...")
    try:
        val = _query_sync_value(db_url, "SELECT name FROM users LIMIT 1;")
        if val is not None:
            R.ok(f"SELECT name FROM users LIMIT 1 → '{val}'")
        else:
            R.warn("SELECT name FROM users LIMIT 1 → NULL (用户表可能为空)")
    except Exception as e:
        R.bad(f"DB 查询失败: {e}")

    # --- pgvector: document_chunks.embedding 列类型 ---
    print(f"\n  检查 pgvector embedding 列...")
    try:
        result = _query_sync(
            db_url,
            "SELECT column_name, udt_name FROM information_schema.columns "
            "WHERE table_name = 'document_chunks' AND column_name = 'embedding';",
        )
        if result:
            udt = result[0].get("udt_name", "")
            # pgvector 的 Vector 类型在 pg 中显示为 'vector'
            if udt == "vector":
                R.ok(f"document_chunks.embedding 列类型 = 'vector' (pgvector)")
            else:
                R.warn(f"document_chunks.embedding 列 UDT = '{udt}' (期望 'vector')")
        else:
            R.bad("document_chunks.embedding 列不存在")
    except Exception as e:
        R.bad(f"pgvector 列检查失败: {e}")

    # --- pgvector: HNSW 索引 ---
    print(f"\n  检查 HNSW 向量索引...")
    try:
        idx_result = _query_sync(
            db_url,
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE tablename = 'document_chunks' AND indexname LIKE '%embedding%';",
        )
        if idx_result:
            for r in idx_result:
                idx_name = r.get("indexname", "")
                idx_def = r.get("indexdef", "")
                if "hnsw" in idx_def.lower():
                    R.ok(f"HNSW 索引存在: {idx_name}")
                    break
            else:
                R.warn(f"embedding 索引存在但非 HNSW: {[r['indexname'] for r in idx_result]}")
        else:
            R.warn("document_chunks 表上未找到 embedding 索引")
    except Exception as e:
        R.bad(f"HNSW 索引检查失败: {e}")

    # --- pgvector: 实际向量操作 ---
    print(f"\n  测试 pgvector 向量操作...")
    try:
        # 测试向量计算能力
        val = _query_sync_value(
            db_url,
            "SELECT '[1,2,3]'::vector <=> '[4,5,6]'::vector AS dist;",
        )
        if val is not None:
            R.ok(f"向量余弦距离计算成功: dist = {val}")
        else:
            R.bad("向量余弦距离计算返回 NULL")
    except Exception as e:
        R.bad(f"向量操作失败: {e}")


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 7 — PostgreSQL + pgvector 生产环境验证脚本",
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help=f"异步数据库 URL (默认: {DEFAULT_DB_URL})",
    )
    parser.add_argument(
        "--skip-api-test",
        action="store_true",
        help="跳过 API 烟雾测试（不启动后端服务）",
    )
    args = parser.parse_args()

    db_url = args.db_url
    print(f"{_C.BOLD}{_C.CYAN}{'#' * 60}{_C.RESET}")
    print(f"{_C.BOLD}{_C.CYAN}  安诊保 AI — Phase 7 PostgreSQL 生产验证{_C.RESET}")
    print(f"{_C.BOLD}{_C.CYAN}{'#' * 60}{_C.RESET}")
    print(f"  DB URL: {db_url}")
    print(f"  Skip API: {args.skip_api_test}")
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Phase 1: 基础设施预检
    check_infrastructure()

    # Phase 2: 迁移验证
    check_migrations(db_url)

    # Phase 3: 数据完整性
    check_data_integrity(db_url)

    # Phase 4: 种子数据
    check_seed_data(db_url)

    # Phase 5: API 烟雾测试
    check_api_smoke(db_url, skip=args.skip_api_test)

    # Phase 6: 生产模式专项
    check_production_mode(db_url)

    # 总结
    R.summary()

    # 退出码
    sys.exit(0 if not R.failed else 1)


if __name__ == "__main__":
    main()
