#!/bin/bash
# ============================================================
# 安诊保 AI 副驾 — 数据库逻辑备份（pg_dump custom format）
# Task 38（P1 B1）：最小可验证备份方案
#
# 用法:
#   AZB_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
#   AZB_BACKUP_DIR=/tmp/backups \
#   bash scripts/backup_database.sh
#
# 安全:
#   - 凭据仅从环境变量注入，绝不硬编码/打印连接串与密码
#   - dump 文件写入 AZB_BACKUP_DIR（默认 ./backups），不得提交 Git
#   - 失败返回非 0；成功打印安全摘要（文件/size/sha256）
# ============================================================
set -euo pipefail

: "${AZB_DATABASE_URL:?AZB_DATABASE_URL must be set}"
BACKUP_DIR="${AZB_BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

# asyncpg scheme -> libpq scheme（pg_dump 使用）
LIBPQ_URL="$(printf '%s' "$AZB_DATABASE_URL" | sed 's|^postgresql+asyncpg://|postgresql://|')"

TS="$(date +%Y%m%d_%H%M%S)"
FILE="${BACKUP_DIR}/anzhenbao_${TS}.dump"

echo "BACKUP_START ts=${TS} dir=${BACKUP_DIR}"
pg_dump "$LIBPQ_URL" --format=custom --no-owner --no-privileges -f "$FILE"
test -s "$FILE" || { echo "BACKUP_FAILED empty_file" >&2; exit 1; }

SIZE="$(stat -c %s "$FILE")"
SHA="$(sha256sum "$FILE" | awk '{print $1}')"
echo "BACKUP_OK file=${FILE} size=${SIZE} sha256=${SHA}"
