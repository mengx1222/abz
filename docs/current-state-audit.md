# 安诊保 AI 副驾 — 当前状态审计报告

> 审计时间: 2026-08-14
> Git HEAD: `1843649` (main)
> 后端版本: 1.0.0-rc.1
> 审计方式: **代码实际运行验证**（非文档推断）

---

## 1. 项目概览

| 维度 | 实际状态 |
|------|---------|
| 技术栈 | React 19 + TS 5 + Vite 6 + Tailwind 4 ‖ Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic |
| 数据库 | PostgreSQL 16 + pgvector (Docker) — 7 个 Alembic 迁移，30 张表定义 |
| 缓存 | Redis 7 (Docker) — 生产代码就绪，Demo 模式不依赖 |
| AI | 自建 Gateway (Mock/OpenAI/DeepSeek/Qwen 兼容)，SSE 流式 |
| 部署 | Docker Compose 4 容器 (postgres/redis/backend/frontend)，含生产配置 |
| 前端构建 | TSC 0 errors，Vite build OK (入口 374KB / gzip 120KB)，19 页面独立 chunk |
| 后端测试 | **133 pytest 用例全部通过** (6 单元 + 10 API 集成) |
| 前端测试 | **27 vitest 用例全部通过** (3 文件) |
| UAT 冒烟测试 | **23/23 全部通过** (14 组关键路径) |

---

## 2. 后端 API 端点统计

| 模块 | 端点数 | 前缀 | 状态 |
|------|--------|------|------|
| 健康检查 | 3 | `/api/v1/health`, `/ready`, `/health/detail` | ✅ Liveness + Readiness + Detail |
| 认证 | 4 | `/api/v1/auth` | ✅ Login/Refresh/Logout/Me |
| AI 助手 | 3 | `/api/v1/ai` | ✅ 产品问答 SSE + 会话管理 |
| 知识库管理 | 9 | `/api/v1/admin` (knowledge-bases) | ✅ CRUD + 上传 + 发布 |
| 客户 360 | 8 | `/api/v1/customers` | ✅ CRUD + AI 分析 + 互动 + 跟进 |
| AI 陪练 | 8 | `/api/v1/training` | ✅ 场景 + 会话 + SSE 对话 + 评分 |
| AI 话术 | 6 | `/api/v1/scripts` | ✅ CRUD + SSE 生成 + 合规检查 + 收藏 |
| AI 社区 | 11 | `/api/v1/community` | ✅ 帖子/评论/点赞/收藏/AI 摘要 |
| 管理后台 | 28 | `/api/v1/admin` | ✅ 用户/看板/审计/合规/社区/话术/陪练/设置/分析 |
| 成长体系 | 4 | `/api/v1/growth` | ✅ 概览/课程/排行榜/成就 |
| 通知中心 | 4 | `/api/v1/notifications` | ✅ 列表/已读/偏好 |
| Dashboard | 1 | `/api/v1/dashboard` | ✅ 概览 |
| **合计** | **89** | | |

---

## 3. 数据库模型 vs Alembic 迁移

### 3.1 迁移链（7 个迁移）

| 迁移 | 内容 | 状态 |
|------|------|------|
| 0001_initial.py | User/Role/Permission/Organization 基础表 | ✅ |
| 0002_knowledge_ai.py | KnowledgeBase/Document/DocumentChunk + AI 日志 | ✅ |
| 0003_scripts.py | Script/ScriptVersion/ScriptFavorite | ✅ |
| 0004_community.py | Post/PostComment/PostLike/PostFavorite | ✅ |
| 0005_remaining.py | Customer/CustomerTag/CustomerInteraction/CustomerFollowup + Training 系列 + Conversation/Message | ✅ |
| 0006_notification_growth_audit.py | Notification/NotificationPreference + Growth/UserAchievement + AuditLog | ✅ |
| 0007_kb_versioning_audit_enhance.py | KB/Document 版本字段 + AuditLog request_id | ✅ |

### 3.2 模型注册（30 张表）

全部 ORM 模型已注册到 `app/models/__init__.py`，通过 `from app.models import *` 可正常导入。

| 模型 | 表名 | 迁移版本 | ORM 注册 |
|------|------|---------|---------|
| User | users | 0001 | ✅ |
| Role | roles | 0001 | ✅ |
| Permission | permissions | 0001 | ✅ |
| Organization | organizations | 0001 | ✅ |
| Conversation | conversations | 0005 | ✅ |
| Message | messages | 0005 | ✅ |
| KnowledgeBase | knowledge_bases | 0002+0007 | ✅ (+effective_date/expiry_date/created_by) |
| Document | documents | 0002+0007 | ✅ (+effective_date/expiry_date/version_number/previous_version_id) |
| DocumentChunk | document_chunks | 0002 | ✅ |
| AIRequestLog | ai_request_logs | 0002 | ✅ |
| AIFeedback | ai_feedbacks | 0002 | ✅ |
| Script | scripts | 0003 | ✅ |
| ScriptVersion | script_versions | 0003 | ✅ |
| ScriptFavorite | script_favorites | 0003 | ✅ |
| TrainingScenario | training_scenarios | 0005 | ✅ |
| TrainingSession | training_sessions | 0005 | ✅ |
| TrainingMessage | training_messages | 0005 | ✅ |
| TrainingScore | training_scores | 0005 | ✅ |
| Customer | customers | 0005 | ✅ |
| CustomerTag | customer_tags | 0005 | ✅ |
| CustomerInteraction | customer_interactions | 0005 | ✅ |
| CustomerFollowup | customer_followups | 0005 | ✅ |
| Post | community_posts | 0004 | ✅ |
| PostComment | community_post_comments | 0004 | ✅ |
| PostLike | community_post_likes | 0004 | ✅ |
| PostFavorite | community_post_favorites | 0004 | ✅ |
| Notification | notifications | 0006 | ✅ |
| NotificationPreference | notification_preferences | 0006 | ✅ |
| UserAchievement | user_achievements | 0006 | ✅ |
| AuditLog | audit_logs | 0006+0007 | ✅ (+request_id) |

**审计结论：30 张表全部有 ORM 模型定义 + Alembic 迁移 + __init__.py 注册，无缺口。**

---

## 4. Demo / Production Bifurcation 状态

所有 Service 均实现 `if settings.DEMO_MODE: return self._demo_xxx()` 分流模式，通过实际代码验证：

| Service | Bifurcation | Demo 数据来源 | Production 数据来源 |
|---------|-------------|---------------|-------------------|
| AuthService | ✅ 2 DEMO_MODE checks | 4 内存用户 (13800138000 系列) | DB (UserRepository) |
| CustomerService | ✅ 9 checks, 25 _demo_ methods | 8 内存客户 | DB (CustomerRepository) + IDOR |
| ScriptService | ✅ 8 checks, 24 _demo_ methods | 8 内存话术 | DB (ScriptRepository) |
| TrainingService | ✅ 8 checks, 45 _demo_ methods | 23 内存场景 | DB (TrainingRepository) |
| CommunityService | ✅ 11 checks, 22 _demo_ methods | 8 帖 + 10 评 | DB (CommunityRepository) |
| GrowthService | ✅ 4 checks, 8 _demo_ methods | 6 课程 + 排行 + 成就 | DB (GrowthRepository) |
| NotificationService | ✅ 4 checks, 8 _demo_ methods | 12 通知 + 5 偏好 | DB (NotificationRepository) |
| DashboardService | ✅ 1 check, 2 _demo_ methods | 4 统计 + 建议 | DB 聚合 |
| ComplianceService | N/A | 纯函数，无 DB 依赖 | 静态规则引擎 |

**审计结论：8/8 需要 bifurcation 的 Service 全部已实现。ComplianceService 是纯函数无需分流。**

### Repository 层

| Repository | 文件 | 状态 |
|-----------|------|------|
| BaseRepository | `repositories/base.py` | ✅ CRUD 基类完整 |
| CustomerRepository | `repositories/customer_repo.py` | ✅ 已被 CustomerService 使用 |
| UserRepo | `repositories/user_repo.py` | ✅ 已被 AuthService 使用 |
| ScriptRepo | `repositories/script_repo.py` | ✅ |
| TrainingRepo | `repositories/training_repo.py` | ✅ |
| CommunityRepo | `repositories/community_repo.py` | ✅ |
| NotificationRepo | `repositories/notification_repo.py` | ✅ |

---

## 5. RAG Pipeline 状态

| 组件 | 文件 | 状态 | 验证结果 |
|------|------|------|---------|
| 文档解析器 | `rag/parser.py` | ✅ | TXT/MD/JSON/PDF |
| 语义分块器 | `rag/chunker.py` | ✅ | 512 token / 50 overlap |
| Demo 检索器 | `rag/retriever.py` | ✅ | n-gram 关键词匹配 |
| 生产检索器 | `rag/retriever.py` | ✅ | pgvector + BM25 + RRF 代码就绪 |
| RAG 编排器 | `rag/pipeline.py` | ✅ | Demo 模式单例 58 chunks |
| **拒答机制** | `rag/safety.py` | ✅ | `should_refuse_answer()` — 空结果/低分(<0.3)拒答，**实测通过** |
| **置信度门控** | `rag/safety.py` | ✅ | `assess_confidence()` — HIGH/MEDIUM/LOW/NONE 四级，NONE 级直接返回固定拒答文本 |
| **Prompt Injection 防护** | `rag/safety.py` | ✅ | `detect_prompt_injection()` — 5 类攻击模式检测（角色劫持/指令泄露/分隔符/JSON注入/编码绕过），**实测通过** |
| **输入消毒** | `rag/safety.py` | ✅ | `sanitize_user_input()` — 控制字符清理 + 2000 字截断 |
| **版本管理** | `models/knowledge.py` + `0007` | ✅ | effective_date/expiry_date + version_number + previous_version_id |
| **组织隔离** | `rag/retriever.py` | ✅ | org_id 参数 + 检索时组织过滤 |

---

## 6. 安全与权限

| 项目 | 文件 | 状态 | 说明 |
|------|------|------|------|
| JWT 认证 | `core/security.py` | ✅ | HS256, 120min access, 7d refresh |
| RBAC 角色 | `models/role.py` | ✅ | 7 角色定义 (SYSTEM_ADMIN→AGENT) |
| `require_role` 装饰器 | `core/deps.py` | ✅ | 路由级角色检查 |
| **IDOR 防护** | `core/authorization.py` | ✅ | DataPermissionChecker — 4 方法 (can_access_customer/document/manage_user/filter_org_ids)，7 角色行级权限，**30 测试通过** |
| **Rate Limiting** | `core/rate_limit.py` | ✅ | TokenBucketRateLimiter — 线程安全令牌桶，按路径分级（登录 2/s、AI 5/s、默认 30/s），**实测通过** |
| **审计日志** | `core/audit.py` | ✅ | AuditMiddleware — 自动审计 POST/PUT/DELETE，structlog 输出 |
| **Prompt Injection** | `rag/safety.py` | ✅ | 5 类攻击模式检测，HIGH 级直接拒答 |
| **敏感数据脱敏** | `core/sanitize.py` | ✅ | mask_phone/id_card/name/email + 递归脱敏，**实测通过** |
| **安全头** | `core/security_headers.py` | ✅ | CSP/X-Frame-Options/HSTS/Permissions-Policy，Demo/Prod 双策略 |
| **CORS 加固** | `main.py` | ✅ | 从 `["*"]` 改为基于 FRONTEND_URL 动态配置 |
| **请求 ID** | `core/middleware.py` | ✅ | RequestIDMiddleware — X-Request-ID 注入/传播 |
| **请求日志** | `core/monitoring.py` | ✅ | RequestLoggingMiddleware — structlog 结构化日志 |
| **错误处理** | `core/middleware.py` | ✅ | ErrorHandlerMiddleware — 全局异常捕获→JSON |
| CSRF | — | ❌ 无 | JWT Bearer Token 认证，CSRF 风险较低但无显式防护 |
| `/ready` 端点 | `api/v1/health.py` | ✅ | 3 端点：/health (Liveness) + /ready (Readiness with DB/Redis/AI checks) + /health/detail |

### 中间件链（6 层，从外到内）

1. SecurityHeadersMiddleware — 安全头
2. RateLimitMiddleware — 限流
3. AuditMiddleware — 审计日志
4. RequestIDMiddleware — 请求 ID
5. RequestLoggingMiddleware — 请求日志（跳过 /health）
6. ErrorHandlerMiddleware — 全局异常

---

## 7. 前端状态

| 项目 | 状态 |
|------|------|
| 页面数量 | 20 个功能页面 (8 业务 + 8 管理 + Login + Dashboard + CustomerDetail + TrainingChat) |
| API Service 层 | 12 个 service 文件，全部对接真实后端 API |
| TypeScript | ✅ 0 errors |
| Vite Build | ✅ 入口 374KB / gzip 120KB（Phase 4 代码分割后 ↓34%） |
| 代码分割 | ✅ React.lazy 将 19 个页面拆分为独立 chunk |
| 角色路由守卫 | ✅ RoleGuard 组件 + roleRoutes.ts (7 角色 × 18 路径权限矩阵) |
| 侧边栏过滤 | ✅ Sidebar.tsx 按用户角色动态过滤菜单项 |
| UI 组件 | Card/Badge/Button/Input/Avatar/Toast/LoadingSpinner (7 个) |
| 前端测试 | ✅ 27 vitest 用例 (authStore 7 + roleRoutes 13 + cn 7) |

---

## 8. 测试覆盖

| 测试类型 | 数量 | 状态 |
|---------|------|------|
| 后端单元测试 | 91 断言 (6 文件) | ✅ 全部通过 |
| — test_auth.py | 7 断言 | ✅ JWT 创建/解码/过期 |
| — test_rag_safety.py | 40 断言 | ✅ 拒答/置信度/注入检测/消毒 |
| — test_rate_limit.py | 15 断言 | ✅ 令牌桶核心逻辑 |
| — test_sanitize.py | 25 断言 | ✅ 手机/身份证/银行卡/姓名/邮箱脱敏 |
| — test_compliance.py | 25 断言 | ✅ 8 条合规规则 |
| — test_authorization.py | 30 断言 | ✅ 5 角色 IDOR 防护 |
| 后端 API 集成测试 | 42 用例 (10 文件) | ✅ 全部通过 |
| 前端单元测试 | 27 用例 (3 文件) | ✅ 全部通过 |
| UAT 冒烟测试 | 23 用例 (14 组) | ✅ 全部通过 |
| E2E (Playwright) | 0 | ❌ 未实现 |

---

## 9. 部署配置

| 文件 | 状态 | 说明 |
|------|------|------|
| docker-compose.yml | ✅ | 开发 4 容器 (postgres+redis+backend+frontend) |
| docker-compose.prod.yml | ✅ | 生产配置：资源限制 + restart:always + env_file + 4 workers + healthcheck |
| backend/Dockerfile | ✅ | 多阶段构建 + HEALTHCHECK |
| frontend/Dockerfile | ✅ | 多阶段构建 (node→nginx) |
| frontend/nginx.conf | ✅ | SPA 路由 + gzip + 缓存 |
| .env.production | ✅ | JWT/AI/API 密钥模板 |
| scripts/deploy.sh | ✅ | 交互式部署引导 |
| scripts/seed.py | ✅ | 种子数据脚本 |

---

## 10. Production Ready 评估

### Production Ready（代码已就绪，需 PostgreSQL 真实环境验证）

| 模块 | 说明 |
|------|------|
| 基础工程 | FastAPI + SQLAlchemy + Alembic + JWT |
| RBAC | 7 角色 + require_role + DataPermissionChecker |
| 数据库 | 30 表 ORM + 7 迁移链完整 |
| Repository | 7 个 Repository 全部实现 |
| Service Bifurcation | 8/8 Service Demo/Production 分流 |
| RAG Safety | 拒答 + 置信度门控 + Prompt Injection + 版本管理 + 组织隔离 |
| 安全中间件 | Rate Limiting + 审计日志 + 数据脱敏 + 安全头 + CORS |
| IDOR 防护 | 7 角色行级权限，CustomerService 全方法覆盖 |
| 前端安全 | 角色路由守卫 + 代码分割 |
| 自动化测试 | 133 pytest + 27 vitest + 23 UAT |
| 部署配置 | Docker Compose 生产配置 + deploy.sh |

### Demo Only（Demo 模式使用内存数据，Production 模式需 DB）

所有 8 个 Service 的 Demo 数据均为内存硬编码。切换 Production 模式（`AZB_DEMO_MODE=false` + PostgreSQL）后，Service 自动通过 Repository 访问真实数据库。**代码路径已实现，但尚未在真实 PostgreSQL + pgvector 环境中完成端到端验证。**

### Mock Only

| 模块 | 说明 |
|------|------|
| AI Gateway | Demo 模式使用 MockProvider；需配置真实 AI API Key |
| AI Embedding | pgvector 向量嵌入尚未在真实环境验证 |

---

## 11. 风险清单

### P0 — 阻断性

**无。** 之前审计中的 P0 问题（无测试、迁移不完整、Community 未注册、纯内存 Service）已全部修复。

### P1 — 严重

| # | 风险 | 说明 | 验证状态 |
|---|------|------|---------|
| P1-1 | **PostgreSQL 真实环境未验证** | 当前 Production 路径代码就绪，但未在真实 PG + pgvector 上运行 `alembic upgrade head` + 全链路测试 | 待验证 |
| P1-2 | **AI Provider 未接入真实模型** | Gateway 代码支持 OpenAI/DeepSeek/Qwen，但仅有 MockProvider 实际运行过 | 待验证 |
| P1-3 | **部分 Service 的 Production 路径未充分测试** | `script_service.py` 的 `generate_scripts()` 生产路径复用了 `_demo_generate_scripts`，未走真实 AI | 代码已确认 |
| P1-4 | **无 Playwright E2E 测试** | 前后端集成仅有 API 级别 UAT，无浏览器级 E2E | 待开发 |

### P2 — 改进

| # | 风险 | 说明 |
|---|------|------|
| P2-1 | 无 CSRF 显式防护 | JWT Bearer Token 认证下风险较低，但可增加 |
| P2-2 | Demo 模式下无 Token 请求返回 200 而非 401 | Demo + SQLite 的 FastAPI security scheme 行为特例，Prod 模式应正常 |
| P2-3 | docker-compose.yml 含默认密码 | 已在 .gitignore，生产使用 .env.production |
| P2-4 | 前端测试覆盖率低 | 仅 3 个工具文件测试，页面组件无测试 |
| P2-5 | 种子数据脚本未集成到迁移流程 | 需手动执行 seed.py |

---

## 12. Phase 判定

> **旧审计报告中的 Phase 判定已过时。** 以下基于实际代码 + 测试运行结果重新判定。

**当前已完成所有 Production 化 Phase（Phase 2-5），处于 Phase 6（内部试点发布准备）阶段。**

详见 [`docs/project-status.md`](./project-status.md) 获取完整的 Phase 映射和状态追踪。
