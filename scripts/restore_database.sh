#!/bin/bash
# ============================================================
# 安诊保 AI 副驾 — 数据库恢复（pg_restore，custom format）
# Task 38（P1 B1）：与 scripts/backup_database.sh 配套
#
# 用法:
#   AZB_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
#   bash scripts/restore_database.sh /path/to/anzhenbao_YYYYmmdd_HHMMSS.dump
#
# 行为:
#   - 目标库执行 --clean --if-exists（重建对象），实现"干净恢复目标"
#   - 恢复失败返回非 0；成功打印安全摘要
#   - 不打印连接串/密码
# ============================================================
set -euo pipefail

: "${AZB_DATABASE_URL:?AZB_DATABASE_URL must be set}"
DUMP="${1:?usage: restore_database.sh <dumpfile>}"

test -f "$DUMP" || { echo "RESTORE_FAILED missing_dump $DUMP" >&2; exit 1; }
test -s "$DUMP" || { echo "RESTORE_FAILED empty_dump $DUMP" >&2; exit 1; }

LIBPQ_URL="$(printf '%s' "$AZB_DATABASE_URL" | sed 's|^postgresql+asyncpg://|postgresql://|')"

echo "RESTORE_START dump=${DUMP}"
pg_restore "$LIBPQ_URL" --clean --if-exists --no-owner --no-privileges "$DUMP"
echo "RESTORE_OK dump=${DUMP}"
