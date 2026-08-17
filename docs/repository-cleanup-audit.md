# 仓库清理审计 — 安诊保 AI 副驾

> 审计日期：2026-08-17
> 审计基线：Git HEAD `575f8f2`（main）
> 目的：把仓库从「长期开发仓库」整理为「可交付的正式项目仓库」

---

## 1. 审计方法

- 拉取 `main` 分支完整快照（tarball，1820 个 Git 跟踪条目）
- 对每个可疑目录/文件执行引用扫描：
  - 代码引用（`backend/`、`frontend/`）
  - CI 引用（`.github/workflows/`）
  - Docker 引用（`docker-compose*.yml`、`Dockerfile`）
  - 文档引用（`docs/`、`README.md`）
  - 脚本引用（`Makefile`、`scripts/`）
- 全仓 Secret 扫描（排除 `skills/` 大数据目录后无命中）

---

## 2. 清理决策总表

| 路径 | 类型 | 条目数 | 代码引用 | CI 引用 | Docker 引用 | 文档引用 | 运行时必需 | 测试必需 | 决策 | 风险 |
|------|------|--------|---------|---------|-------------|----------|------------|----------|------|------|
| `download/` | 过程产物 | 1 | 无 | 无 | 无 | 仅历史 project-audit | 否 | 否 | **删除** | 无 |
| `upload/` | 过程产物（Codex Prompt） | 2 | 无 | 无 | 无 | 仅历史 project-audit | 否 | 否 | **删除** | 无 |
| `tool-results/` | 工具输出 | 12 | 无 | 无 | 无 | 无（仅 .gitignore 忽略规则） | 否 | 否 | **删除** | 无 |
| `skills/` | 无关技能集 | 1479 | 无 | 无 | 无 | 无 | 否 | 否 | **删除** | 无 |
| `.env`（根） | 本地环境残留 | 1 | 无（已被 .gitignore 忽略） | 无 | 无 | 无 | 否 | 否 | **移出 Git 跟踪** | 无（内容仅本地 sqlite 路径，无真实密钥） |
| `docs/project-audit.md` | 历史审计 | 1 | 无 | 无 | 无 | 自标记过时（指向 current-state-audit） | 否 | 否 | **移入 docs/archive/** | 无 |
| `scripts/deploy.sh` | 部署脚本 | 1 | — | 无 | 引用 compose | — | 是 | 否 | **最小修复** | 路径与 compose.prod 不一致（见 §3） |

**保留**：`backend/`、`frontend/`、`docs/`、`.github/`、`scripts/`（deploy.sh 修复后）、`Makefile`、`docker-compose*.yml`、`.env.example`、`backend/.env.example`、`backend/.env.production`（占位模板）、`README.md`（重写）、`worklog.md`。

---

## 3. 删除目录详情

### 3.1 `download/`

- 内容：`download/README.md` — 仅一句话占位（"Here are all the generated files."）
- 引用扫描：`grep -r "download/"` 全仓（排除自身）→ 仅在 `docs/project-audit.md`（历史审计，即将归档）出现
- 结论：生成文件占位目录，非产品资源 → **删除**

### 3.2 `upload/`

- 内容：2 个开发过程 Prompt：
  - `安诊保 AI 副驾｜Codex 0→1 产品研发总控 Prompt.md`
  - `安诊保 AI 副驾｜Codex 终极产品收口与生产化总控 Prompt.md`
- 引用扫描：无任何代码/CI/Docker/当前文档引用
- 结论：聊天过程 Prompt 不属于产品源码 → **删除**（工程规范类内容若需要，另行维护在 `docs/engineering/`，本次无有效存量）

### 3.3 `tool-results/`

- 内容：12 个 `read_*.txt`（自动工具读取输出）
- 引用扫描：无；`.gitignore` 第 52 行已有 `tool-results/` 忽略规则（保留）
- 结论：本地工具产物误提交 → **删除**

### 3.4 `skills/`

- 内容：1479 个文件 / 约 60MB，67 个技能目录（gaokao / fortune / podcast / xlsx / web-search / image-generation / interview / resume / study / finance 等），与本项目（安诊保 AI 副驾）无产品关联
- 引用扫描：`grep -r "skills/"` 排除自身 → `.github/`、`backend/`、`frontend/`、`docs/`、`Makefile`、`README.md`、`scripts/` 全部**零命中**
- 结论：非本项目运行/构建/CI/文档依赖 → **整目录删除**

### 3.5 `.env`（根目录）

- 当前被 Git 跟踪，内容：`DATABASE_URL=file:/home/z/my-project/db/custom.db`（本地开发 sqlite 路径，无真实密钥）
- `.gitignore` 已含 `.env` 规则 → 删除后不会再次提交
- 结论：**从 Git 跟踪移除**；`.env.example` / `backend/.env.example` / `backend/.env.production`（占位模板）保留

### 3.6 `docs/project-audit.md`

- 内容：2025-07 Phase 0 初始基线审计，文档头部自标记「已过时 → 见 current-state-audit.md」
- 结论：有历史价值 → **移入 `docs/archive/project-audit-initial.md`**（不丢失）

---

## 4. 最小部署修复

`scripts/deploy.sh` 检查/加载 `backend/.env.production`，但：
- `docker-compose.prod.yml` 使用 `env_file: .env.production`（相对 compose 文件目录 = **根目录**）
- `.github/workflows/production-validation.yml` 在**根目录**生成 `.env.production`

路径不一致会误导部署。**最小修复**：deploy.sh 改为检查/加载根目录 `.env.production`，提示语引用 `backend/.env.production` 占位模板。

---

## 5. Secret 扫描结果

- 当前工作树（排除 `skills/`）：**无真实密钥命中**（无 sk-/ghp_/github_pat/AKIA/PRIVATE KEY 等）
- 根 `.env` 仅含本地 sqlite 路径，无真实凭据
- 真实 AI Key / GitHub PAT 均未进入仓库（由 GitHub Secrets 注入，见 `.github/workflows/`）

---

## 6. 清理后目标结构

```
/
├── .github/            # CI workflows（backend-tests / e2e-playwright / production-validation / real-ai-smoke）
├── backend/            # FastAPI + SQLAlchemy + RAG + AI Gateway
├── frontend/           # React + Vite + TypeScript
├── docs/               # 项目文档（含 archive/ 历史归档）
├── scripts/            # deploy.sh（部署引导）
├── .env.example        # 环境变量模板
├── .gitignore
├── docker-compose.yml          # 开发编排
├── docker-compose.prod.yml     # 生产编排
├── Makefile
├── README.md
└── worklog.md
```
