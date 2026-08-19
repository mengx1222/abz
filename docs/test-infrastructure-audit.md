# Test Infrastructure Audit — Task 26（E2E / Seed / Production-like）

> 建立时间：2026-08-19
> 基线：main@36077cf（Task 25 完成）→ 完成：main@4a4bc5a（代码链，docs 提交后更新）
> 方法：100% Cloud-only（GitHub API 读码 + GitHub Actions 验证）

---

## 1. Workflow → Database → Seed → User/Role → Org → KB/Document → API → Assertions 链路图

| Workflow | DB（独立容器） | Migration | Seed | 关键环境 | 测试内容 |
|----------|----------------|-----------|------|----------|----------|
| `backend-tests`（CI） | sqlite（测试内） | 无 | conftest（demo 账号） | `AZB_DEMO_MODE=true`（conftest） | 全量 pytest（unit + API 集成） |
| `backend-tests`（backend-pg job） | **docker run pgvector/pgvector:pg16**（独立） | `alembic upgrade head`（干净库，每轮） | `python -m scripts.seed` | `AZB_DEMO_MODE=false`（测试内 monkeypatch） | PG 集成 7 文件：pg_integration / permission_pg / ingestion_pg / **org_tree_pg（新增）** / kb_crud / document_management / e2e_seed_idempotency |
| `e2e-playwright` | services postgres（独立） | alembic | scripts.seed + **e2e_seed_knowledge** | `DEMO_MODE=false` + mock/real AI | Playwright E2E（24：Login/Dashboard/Customers/Growth/Knowledge/ProductQA/Scripts/Training/Admin） |
| `production-validation` | docker compose postgres（独立） | alembic | scripts.seed | `DEMO_MODE=false` | phase7/phase8 + **pytest 全量**（PG 测试用 compose PG） |
| `real-ai-smoke`（opt-in） | 无（API 冒烟） | — | — | 真实 DashScope | phase9 脚本 |

**结论**：各 workflow 使用独立 PG 容器 → 无跨 workflow 数据库污染（Step 8 满足）；backend-pg 每轮在干净 PG 上执行完整 migration chain + seed（Step 9 满足）。

## 2. 历史已知风险逐项确认（Step 2 ①~⑩）

| # | 风险 | 当前状态 | 证据 |
|---|------|----------|------|
| ① | N8 共享 KB（org=NULL）污染权限测试 | **已消除**：backend-pg 各权限测试用随机 suffix 自建 KB；`test_permission_pg`/`test_ingestion_pg` 防御性清理 org=NULL KB（backend-pg 初始无共享 KB，因为 `scripts.seed` 不建 KB、E2E seed 只在 E2E 容器跑） | test_permission_pg._seed L86 |
| ② | N7 修复后组织树 seed 可用性 | **发现真实 bug（本任务修复）**：production + async 下 `Organization.children`（lazy=selectin）访问抛 MissingGreenlet 被静默吞 → HQ/BRANCH_ADMIN 范围退化仅本组织 | backend-pg 实测 + `failed_to_collect_child_orgs` warning |
| ③ | RAG permission 同时验证 role+org 且不被污染 | **满足**：permission_pg（A/B/D/E/G/J/L）、role_filter、org_scope 覆盖 role+org+vector+BM25+leakage；随机 suffix 隔离 | tests/rag/ |
| ④ | E2E seed 与 API contract 一致 | **满足**：K-1~K-3 验证 Knowledge/Document API；Admin API（/admin/community 等）确认 Demo-only（Task 24/25 记录） | e2e/knowledge + admin |
| ⑤ | 生产模式不依赖 DEMO_MODE=true | **满足**：backend-pg/E2E/Prod 均 DEMO_MODE=false；conftest 默认 true 但 PG 测试 monkeypatch false | workflows + tests |
| ⑥ | E2E 不通过 mock API 假绿 | **满足**：E2E 走真实 backend（DEMO_MODE=false + 真实 PG/Redis；AI provider 无 key 时回退 mock 仅影响 AI 响应，不 mock API 层） | e2e-playwright.yml |
| ⑦ | seed 稳定可重复（唯一约束/重复数据） | **满足**：scripts.seed get-or-create（roles/perms/orgs/users）；e2e_seed_knowledge 幂等（Task 24：存在即跳过+计数 WARN）；测试随机 suffix 避免 phone/KB 名冲突 | seed.py / e2e_seed_knowledge.py |
| ⑧ | 干净 PG 完整 migration | **满足**：backend-pg 每轮 docker run 全新容器 + alembic upgrade head（0001→0009 顺序）；E2E/Prod 同样 | backend-tests.yml / e2e-playwright.yml |
| ⑨ | seed cleanup 不删其他数据 | **满足**：仅按 KB_NAME 删自己的 E2E KB（test_e2e_seed_idempotency）或 org=NULL KB（权限测试防御）；不删业务数据 | tests |
| ⑩ | 跨 workflow 不可预测污染 | **满足**：独立容器/服务 | workflows |

## 3. 发现的真实 bug 与修复

### Bug 1：Production 模式组织树递归静默失效（Confirmed，backend-pg 实测）

- **发现**：`test_org_tree_pg.py`（本任务新增，真实 async + PG + DEMO_MODE=false）
  - 修复前：`HQ_ADMIN` 仅返回 `[本组织]`（缺 Branch/Team）；`BRANCH_ADMIN` 仅返回 `[本组织]`（缺 Team）→ 断言失败
  - 日志证据：`failed_to_collect_child_orgs` warning（`DataPermissionChecker._collect_child_org_ids` 内 `except Exception` 吞掉 MissingGreenlet）
- **根因**：`Organization.children` 为 `lazy="selectin"`；`get_current_user` 查询 User 时未 eager-load 组织树 → async 下同步访问 `org.children` 抛 `MissingGreenlet` → 被 `except Exception` 静默捕获 → 返回 `[root_org_id]`。影响：HQ_ADMIN/BRANCH_ADMIN 的「本机构+下属机构」范围（客户/文档/RAG org scope）全部静默收窄为仅本组织（功能缺陷；安全方向为收紧，非泄露）。
- **修复（最小，不改权限模型）**：`deps.py get_current_user` 查询嵌套 `selectinload` 组织树（`org → children → children`，HQ→Branch→Team 3 层）；`test_org_tree_pg._load_user` 同步加载方式。
- **测试**：`tests/rag/test_org_tree_pg.py`（3 用例，backend-pg 纳入）——HQ 全子树 / BRANCH 子树不含兄弟 / TEAM 仅本团队。

## 4. 本任务修改文件

| 文件 | 改动 |
|------|------|
| `backend/app/core/deps.py` | get_current_user 嵌套 selectinload 组织树（Bug 1 修复） |
| `backend/tests/rag/test_org_tree_pg.py` | 新增（组织树递归 production 实测） |
| `.github/workflows/backend-tests.yml` | backend-pg pytest 纳入 test_org_tree_pg |
| `docs/test-infrastructure-audit.md` | 本文件（新建） |

## 5. 测试矩阵（最终数字以 GitHub Actions 为准）

| 域 | 预期 |
|----|------|
| Backend pytest | 全量通过（278+ 无回归；test_authorization unit 逻辑不变） |
| backend-pg | **38 passed（35 + org_tree 3）** ✅ |
| Frontend tsc/vitest/build | 无改动，无回归 |
| E2E | 24（无改动，无回归） |
| Production Validation | ✅（pytest 全量含新测试） |
| 干净 migration + seed | backend-pg 每轮验证 ✅ |
| seed 幂等 | scripts.seed / e2e_seed_knowledge get-or-create ✅ |

## 6. 仍存在的限制（记录，不扩大范围）

- **组织树 eager-load 深度固定 3 层**（HQ/BRANCH/TEAM 模型约束）：若未来组织层级超过 3 层，`get_current_user` 的 selectinload 需加深（或改 `_collect_child_org_ids` 为显式递归查询）
- **Admin 管理 API Demo-only**（/admin/community|scripts|compliance|users|analytics|settings）：production 后端下返回 `_DEMO_*` 数据 → 测试可确定性断言但非真实 DB；属 Admin Management Productionization 后续任务
- **E2E KB「E2E产品知识库」org=NULL 共享语义**：显式命名——合法产品行为「未限定组织的共享知识库（仍受 allowed_roles 约束）」（model comment + retriever 同语义），E2E 环境专属容器，不污染其他 workflow
- **测试数据残留**：backend-pg 各测试用随机 suffix 创建 org/user/KB 且不清理（与既有测试风格一致，随机命名天然隔离，无唯一约束冲突）
