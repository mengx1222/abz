# Seed Data & Deployment Consistency Audit（Task 35 — P2-4）

> 审计日期：2026-08-20
> 基线：main@`4f413b6`（Task 34 全绿：Backend 296/45、PG 45、Vitest 107、E2E 27、Prod ✅）
> 方法：100% Cloud-only —— GitHub API 读取 seed 脚本、CI workflows、Docker 配置、版本文件，无本地 clone/测试
> 范围：Seed 幂等性 / 数据模型一致性 / CI 环境一致性 / Docker 部署一致性；只读审计 + 最小修复

---

## 1. Current State

### 1.1 Backend Seed（`backend/scripts/seed.py`，338 行）
- **幂等性：✅ 全部 6 段均为 exists-check-skip 模式**：
  1. Roles（按 `code` 查重）→ 跳过已存在
  2. Permissions（按 `code` 查重）→ 跳过已存在
  3. Role-Permission 绑定（按 `role_id+permission_id` 查重）→ 新增绑定可补插（seed 可**增量**演进）
  4. Organizations（按 `name` 查重，父先于子顺序创建）→ 跳过已存在
  5. Demo Users（按 `phone` 查重）→ 跳过已存在
  6. Training Scenarios（`training_service.seed_training_scenarios` 按 `title` 查重）→ 幂等
- 数据符合生产模型：Organization（HQ/BRANCH/TEAM 三级树）/ Role（7 标准角色，decisions.md §6）/ Permission（20 项）/ User（4 演示用户，`demo_mode=True`）/ TrainingScenario（内置场景）。
- 依赖：运行前需 `alembic upgrade head`（compose.prod 启动命令已保证顺序：`alembic upgrade head && python -m scripts.seed && uvicorn`）。

### 1.2 CI Environment（`.github/workflows/`）
| Workflow | 环境一致性 | 说明 |
|----------|-----------|------|
| backend-tests | ✅ | conftest 设 `AZB_DEMO_MODE=true`；backend-pg job 用 `AZB_DATABASE_URL` + `AZB_TEST_DATABASE_URL`（postgres 服务容器，anzhenbao_test） |
| backend-pg | ✅ | 独立 PG16+pgvector 容器，`alembic upgrade head` 后跑集成测试 |
| e2e-playwright | ✅ | `AZB_APP_ENV=production` + `AZB_DEMO_MODE=false` + 真实 AI Secrets（qwen 默认 / 缺 key 降级 mock）+ 幂等 KB seed |
| production-validation | ✅ | 内联生成根 `.env.production`（`AZB_AI_PROVIDER=mock`）+ compose.prod 全栈验证 |
| 统一性 | ✅ | 全部使用 `AZB_` 前缀，无跨环境变量名冲突 |

### 1.3 Docker / Deployment
- `docker-compose.prod.yml`：backend `command` 自动执行 `alembic upgrade head && python -m scripts.seed` ✅；`depends_on`（postgres/redis `service_healthy`）✅；healthcheck（backend curl `/api/v1/ready`，frontend 无 healthcheck 但 depends_on backend healthy）✅；PG/Redis 资源限制 + 持久卷 ✅。
- `backend/Dockerfile`：多阶段，runtime 含 `curl`（healthcheck 依赖）✅；`HEALTHCHECK` 指向 `/api/v1/health` ✅。
- **`frontend/Dockerfile`：使用 `npx vite build` 绕过 tsc**，注释称「大量既有 TS 错误（P1-6）」—— **P1-6 已于 Task 19 RESOLVED（tsc -b 0 errors + CI 硬门禁）**，生产镜像构建与 CI 构建（`npm run build` = tsc -b && vite build）不一致（见 §2）。
- `env_file: .env.production`（compose 相对根目录）：**根目录 .env.production 未提交**（.gitignore，部署时创建）；模板在 `backend/.env.production`（CHANGE_ME 占位）；CI 内联生成根文件 → 部署时须复制模板到根目录并填真实值（见 deployment.md）。

## 2. Found Issues

| # | 级别 | 问题 | 证据 |
|---|------|------|------|
| I1 | **P2（修复）** | **版本号不一致**：`config.py::APP_VERSION="1.0.0-rc.1"` ≠ pyproject/package.json/README `0.1.0`；`/api/v1/health` `/ready` `/health/detail` 对外返回 `1.0.0-rc.1` | config.py L27 vs pyproject.toml L3 vs package.json L4 |
| I2 | **P2（修复）** | **生产镜像构建与 CI 不一致**：frontend/Dockerfile 用 `npx vite build` 绕过 tsc（P1-6 已修复，注释过时）→ 镜像未受 tsc 硬门禁保护，可能产出与 CI 不一致产物 | frontend/Dockerfile L18-19 |
| I3 | **P2（补测）** | **`scripts/seed.py` 无回归测试**（仅 e2e_seed_knowledge 有 test_e2e_seed_idempotency.py）——重复部署失败/重复数据风险无护栏 | tests/ 树中仅 test_e2e_seed_idempotency.py 含 seed |
| I4 | **Recorded（不改代码）** | seed.py 无条件创建 4 个演示用户（密码 `888888`，`demo_mode=True`），**与 DEMO_MODE 无关**——若对正式生产库执行 seed，将存在默认凭据。PILOT 可接受（试点用户即演示用户）；**PRODUCTION READY 前必须轮换/关闭** | seed.py L149-178, L293-315 |
| I5 | **Recorded（不改代码）** | 组织按 `name` 匹配（半删除状态边缘：重建时 parent 可能指向缺失组织） | seed.py L266-291（Task 24 已记录 Existing Limitation） |
| I6 | **Recorded（不改代码）** | root `.env.production` 未提交（部署时创建）；模板位于 `backend/.env.production` —— 部署文档须明确复制路径 | compose.prod L57-58 + .gitignore |

## 3. Risk Level

- **整体：LOW-MEDIUM**。Seed 幂等（重复部署不会失败/重复数据）；CI 环境一致；唯一上传/认证等安全面已由 Task 31/34 收敛。
- I1/I2 为环境一致性偏差（对外版本号失真 + 生产构建未对齐 CI 门禁）——不影响运行，但影响 Release Candidate 一致性判断 → **本次修复**。
- I4 为默认凭据风险（仅对正式生产库执行 seed 时成立）→ 记录 + 文档化，纳入 PRODUCTION READY 前置项。

## 4. Recommended Action

1. **I1 修复**：`config.py::APP_VERSION` 对齐 `"0.1.0"`（与 pyproject/package.json/README/release-verification 一致）。
2. **I2 修复**：`frontend/Dockerfile` 改 `RUN npm run build`（tsc -b && vite build），删除过时 P1-6 注释——生产镜像构建与 CI 硬门禁对齐。
3. **I3 补测**：新增 `backend/tests/knowledge/test_seed_idempotency.py`（backend-pg）——首次运行成功 / 二次运行成功 / 无重复数据（每 code/name/phone 恰好 1 条）/ 角色-权限绑定正确。
4. **I4 文档化**：deployment.md / release-readiness 增加「seed 演示用户默认凭据」说明与 PRODUCTION READY 前置项。
5. **I5/I6**：维持记录（不扩大范围）。

## 5. 已验证无需修改

- seed 幂等性本身 ✅（无需 get_or_create 改造——现有 exists-check-skip 等价且更稳）
- CI env 变量一致性 ✅（AZB_ 前缀统一）
- 迁移执行顺序（compose 启动链 alembic → seed → uvicorn）✅
- healthcheck / service dependency ✅
- e2e_seed_knowledge 幂等 ✅（Task 24 已测，3 用例）
