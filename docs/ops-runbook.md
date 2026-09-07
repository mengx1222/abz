# 运维手册（Ops Runbook）— 安诊保 AI 副驾

> 建立时间：2026-09-07
> 适用范围：生产/试点部署（Docker Compose 或便携包模式）的日常运维
> 前置阅读：[deployment.md](deployment.md)、[current-state-audit.md](current-state-audit.md)

---

## 1. 上线前配置清单（一次填空，全部必做）

| 项 | 位置 | 说明 |
|----|------|------|
| 生产 secrets | 根目录 `.env.production`（从 `backend/.env.production` 模板复制） | `AZB_JWT_SECRET_KEY`（≥32 位随机串）、`AZB_DEMO_PASSWORD`（试点强密码）、`AZB_AI_API_KEY`、`POSTGRES_PASSWORD`；所有 `CHANGE_ME` 必须替换 |
| 代理信任 | `.env.production` 的 `AZB_TRUST_PROXY` | 前面有 Nginx/Caddy/Cloudflare 时设 `true`（否则限流与审计日志按代理 IP 计数）；**要求代理层剥离客户端伪造的 XFF/X-Real-IP**。直连暴露保持 `false` |
| HTTPS | 反向代理层 | 内部试点可先 HTTP+IP；正式商用必须 HTTPS（Caddy 自动证书或 Cloudflare 托管域 + 命名隧道） |
| 防火墙 | 服务器 + 云安全组 | 仅放行 22/80/443；PostgreSQL 5432、Redis 6379 **不得**对外网开放（compose 已绑定 127.0.0.1，保持） |
| 端口收敛 | compose | 生产建议 backend 不直接映射 8000 到公网，由前端 Nginx 统一代理 `/api/` |

## 2. 监控与告警（半天工作量）

当前系统自带：
- `/api/v1/health`（Liveness）、`/api/v1/ready`（Readiness：配置/DB/Redis/AI 四项检查）
- 结构化日志（structlog，含 request_id 全链路）

需要补的外部监控（免费够用）：
1. **UptimeRobot**（免费 50 个监控位）：
   - HTTPS 监控 `https://<域名>/api/v1/ready`，间隔 5 分钟
   - 告警通道接 **企业微信/钉钉机器人 webhook**（UptimeRobot 支持 webhook 通知）
2. **日志留观**：`docker compose logs -f backend`；生产建议配 docker log rotation（compose logging.max-size: 50m, max-file: 5）
3. AI 成本哨兵：管理后台 analytics 已有调用量统计，每周看一次 DashScope 账单对齐

## 3. 备份与恢复（脚本与 CI 均已具备，需要"真的在跑"）

每日备份（生产机 crontab）：

```cron
# 每天 03:00 备份 PostgreSQL（脚本位于 scripts/backup_database.sh）
0 3 * * * /opt/anzhenbao/scripts/backup_database.sh >> /var/log/abz-backup.log 2>&1
```

- **异地副本**：备份产物（`*.dump.gz`）每天同步一份到对象存储/另一台机器（`rclone copy` 或 `scp`）
- **恢复演练**：每季度用 `scripts/restore_database.sh` + `scripts/verify_restored_db.py` 做一次真实恢复验证（CI 已有 `database-backup-restore.yml` 持续验证脚本本身可用）
- 便携 Demo 模式（SQLite）：备份 = 拷走 `data/anzhenbao.db`，重启重置是"特性"不是事故

## 4. 容量与压测（2026-09-07 基线）

工具：`scripts/loadtest.py`（仓库自带，httpx 实现）

```bash
# 在任意能访问目标的机器上
pip install httpx
python scripts/loadtest.py --base https://<域名> --users 30 --duration 60
```

开发机首测结论（Docker Desktop + 真实 Postgres/Redis，非生产基线）：
- 30 并发混合读场景：0 错误，吞吐 ~20 RPS，p50 ≈ 1.5s / p95 ≈ 2.3s
- **该数字受开发机负载与限流规则双重压制，不代表生产容量**；上服务器后重测并以服务器数字为准
- 限流设计（2026-09-07 起）：登录用户按 `user_id` 限流（办公室 NAT 不再共享 30/s 桶），未认证按 IP；规则：login 2/s、AI 5/s、默认 30/s（demo 模式 ×5）

**上生产服务器后必做**：重跑上面命令，确认 30 并发 p95 < 1s、错误率 < 0.1%；AI/SSE 长连接场景（陪练、Agent 对话）单独人工并发验证一轮。

## 5. 发布与回滚

- 发布 = `git pull && docker compose -f docker-compose.prod.yml build && docker compose -f docker-compose.prod.yml up -d`（ alembic 迁移在 backend 启动命令自动执行）
- 回滚 = checkout 上一个 tag/commit 重新 build up；数据库迁移回滚慎用（先备份）
- CI（`production-validation.yml`）每次 main 合并自动做生产栈验证，红禁合

## 6. 常见故障

| 症状 | 排查 |
|------|------|
| `/ready` 返回 redis: disconnected | Redis 容器挂/内存不足：`docker compose ps` + `docker logs abz-redis` |
| 登录全部 429 | 检查是否误把反向代理当直连（TRUST_PROXY 配错）或 Redis 计数键堆积 |
| AI 无响应/503 | DashScope Key 额度/网络；`RATE_LIMITER_UNAVAILABLE` ≠ AI 故障，先看 Redis |
| 上传 413 | `MAX_UPLOAD_SIZE_MB`（默认 10MB），按需在 settings 调 |
