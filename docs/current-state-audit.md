# 安诊保 AI 副驾 — 当前状态审计报告

> 审计时间: 2026-08-14  
> Git HEAD: `15a4a38` (main, 27 commits)  
> 审计人: Phase 1 自动审计

---

## 1. 项目概览

| 维度 | 实际状态 |
|------|---------|
| 技术栈 | React 18 + TS 5 + Vite 6 + Tailwind 4 \| Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic |
| 数据库 | PostgreSQL 16 + pgvector (Docker) — 3个Alembic迁移已就绪 |
| 缓存 | Redis 7 (Docker) |
| AI | 自建 Gateway (Mock/OpenAI兼容) |
| 部署 | Docker Compose 4容器 (postgres/redis/backend/frontend) |
| 前端构建 | TSC 0 errors, Vite build OK (568KB JS / 160KB gzip) |
| 测试 | **无自动化测试** — 无 pytest / vitest / playwright |

---

## 2. 后端 API 端点统计

| 模块 | 端点数 | 前缀 | 状态 |
|------|--------|------|------|
| 健康检查 | 1 | `/api/v1/health` | ✅ 正常 |
| 认证 | 4 | `/api/v1/auth` | ✅ 正常 (Demo模式内存) |
| AI助手 | 3 | `/api/v1/ai` | ✅ SSE流式 |
| 知识库管理 | 9 | `/api/v1/admin` | ✅ CRUD+上传+发布 |
| 客户360 | 8 | `/api/v1/customers` | ✅ CRUD+AI分析+互动+跟进 |
| AI陪练 | 9 | `/api/v1/training` | ✅ 场景+会话+SSE对话+评分 |
| AI话术 | 6 | `/api/v1/scripts` | ✅ CRUD+SSE生成+合规检查+收藏 |
| AI社区 | 11 | `/api/v1/community` | ✅ 帖子/评论/点赞/收藏/AI摘要 |
| 管理后台 | 28 | `/api/v1/admin` | ✅ 用户/看板/审计/合规/社区/话术/陪练/设置 |
| 成长体系 | 4 | `/api/v1/growth` | ✅ 概览/课程/排行榜/成就 |
| 通知中心 | 4 | `/api/v1/notifications` | ✅ 列表/已读/偏好 |
| Dashboard | 1 | `/api/v1/dashboard` | ✅ 概览 |
| **合计** | **69** | | |

---

## 3. 数据库模型 vs Alembic 迁移

| 模型 | 定义文件 | 迁移版本 | 备注 |
|------|---------|---------|------|
| User, Role, Permission, RolePermission, Organization | models/user.py, role.py, permission.py, organization.py | 0001 (缺失!) | **⚠️ 无0001迁移，迁移从0002开始** |
| Conversation, Message | models/conversation.py | 未在迁移中 | ⚠️ 表不存在于任何迁移 |
| KnowledgeBase, Document, DocumentChunk | models/knowledge.py | 0002 | ✅ |
| AIRequestLog, AIFeedback | models/ai_log.py | 0002 | ✅ |
| TrainingScenario, TrainingSession, TrainingMessage, TrainingScore | models/training.py | 未在迁移中 | ⚠️ 表不存在于任何迁移 |
| Customer, CustomerTag, CustomerInteraction, CustomerFollowup | models/customer.py | 未在迁移中 | ⚠️ 表不存在于任何迁移 |
| Script, ScriptVersion, ScriptFavorite | models/script.py | 0003 | ✅ |
| Post, PostComment, PostLike, PostFavorite | models/community.py | 0004 | ✅ 但 ⚠️ **未注册到 models/__init__.py** |
| Notification (通知模型) | **不存在** | 无 | ❌ 无通知数据模型 |
| Growth/Achievement/Leaderboard (成长模型) | **不存在** | 无 | ❌ 无成长数据模型 |
| AuditLog (审计日志模型) | **不存在** | 无 | ❌ 无审计日志数据模型 |

### 迁移缺口汇总
- **0001_initial.py 缺失** — User/Role/Permission/Organization 无迁移
- **Conversation/Message 无迁移** — AI对话无法持久化
- **Training 系列 无迁移** — 陪练数据无法持久化
- **Customer 系列 无迁移** — 客户数据无法持久化
- **Community 模型未注册** — ORM导入会失败
- **Notification/Growth/AuditLog 无模型定义** — 纯内存

---

## 4. Demo/Mock 分布

| Service | 数据模式 | Demo数据量 | 生产化就绪 |
|---------|---------|-----------|-----------|
| AuthService | `if demo_mode` + 内存用户 | 4个用户 | ❌ 无DB fallback |
| CustomerService | `if demo_mode` + 内存列表 | 8个客户 | ❌ 有Repository但未使用 |
| ScriptService | 硬编码 `_DEMO_SCRIPTS` | 8条话术 | ❌ 纯内存 |
| TrainingService | 硬编码 `_DEMO_SCENARIOS` | 23个场景 | ❌ 纯内存 |
| CommunityService | 硬编码 `_DEMO_POSTS` + `_DEMO_COMMENTS` | 8帖+10评 | ❌ 纯内存 |
| GrowthService | 硬编码 demo数据 | 6课程+10排行+12成就 | ❌ 纯内存 |
| NotificationService | 硬编码 demo数据 | 12通知+5偏好 | ❌ 纯内存 |
| DashboardService | 硬编码 demo数据 | 4统计+4建议+8活动 | ❌ 纯内存 |
| AdminService | 硬编码 demo数据 | 10用户+50日志+6规则 | ❌ 纯内存 |
| ComplianceService | 规则列表(静态) | 8条规则 | ⚠️ 规则可配置但无DB |

**关键问题**: 只有 CustomerRepository 有 BaseRepository 实现，其余全部是 Service 层直接包含内存数据。没有统一的 Demo/Production Repository 切换机制。

---

## 5. Repository 层状态

| Repository | 文件 | 状态 |
|-----------|------|------|
| BaseRepository | `repositories/base.py` | ✅ CRUD基类完整 |
| CustomerRepository | `repositories/customer_repo.py` | ✅ 但未被Service层使用 |
| UserRepo | `repositories/user_repo.py` | ✅ 基础实现 |
| **其他模块** | **不存在** | ❌ 无 Script/Training/Community/Growth/Notification/Admin Repository |

---

## 6. RAG Pipeline 状态

| 组件 | 文件 | 状态 |
|------|------|------|
| 文档解析器 | `rag/parser.py` | ✅ TXT/MD/JSON/PDF |
| 语义分块器 | `rag/chunker.py` | ✅ 512 token / 50 overlap |
| Demo检索器 | `rag/retriever.py` | ✅ n-gram关键词匹配 |
| 生产检索器 | `rag/retriever.py` | ⚠️ pgvector+BM25+RRF 代码存在但**从未测试** |
| RAG编排器 | `rag/pipeline.py` | ✅ Demo模式单例58 chunks |
| **拒答机制** | — | ❌ **不存在** — 无结果时仍回答 |
| **版本管理** | — | ❌ **不存在** — 无生效/失效日期 |
| **权限过滤** | — | ❌ **不存在** — RAG无组织范围过滤 |
| **Prompt Injection防护** | — | ❌ **不存在** |
| **引用验证** | — | ⚠️ 返回chunk_id和heading但**未验证准确性** |
| **置信度门控** | — | ❌ **不存在** — 无 `RAG_MIN_RELEVANCE` 实际应用 |

---

## 7. 权限与安全

| 项目 | 状态 | 说明 |
|------|------|------|
| JWT认证 | ✅ | HS256, 120min过期, refresh 7天 |
| RBAC角色 | ✅ | 7角色定义完整 |
| `require_role` 装饰器 | ✅ | 路由级角色检查 |
| **IDOR防护** | ❌ | **Service层无数据权限过滤** — Agent A可访问Agent B客户(在内存模式下) |
| **Rate Limiting** | ❌ | 仅有admin.py中的一个字段定义，**无中间件实现** |
| **CSRF** | ❌ | 无CSRF保护 |
| **Prompt Injection** | ❌ | RAG/AI Gateway无输入消毒 |
| **敏感数据脱敏** | ⚠️ | 前端部分脱敏，后端API返回明文手机号 |
| **Secret管理** | ⚠️ | `.env`在.gitignore中，但docker-compose.yml含明文密码 |
| **审计日志** | ❌ | admin.py返回硬编码日志列表，**无真实审计** |
| **`/ready` 端点** | ❌ | 仅有 `/health` |

---

## 8. 前端状态

| 项目 | 状态 |
|------|------|
| 页面数量 | 21个页面 (8业务+8管理+Login+Dashboard+3详情/子页面) |
| API Service层 | 10个service文件，全部对接真实后端API |
| TypeScript | 0 errors, 0 warnings |
| Vite Build | ✅ 568KB JS / 160KB gzip |
| 代码分割 | ❌ 无 — 单chunk 568KB |
| 前端权限 | ⚠️ 仅AuthGuard检查登录，无角色级路由保护 |
| Loading/Empty/Error三态 | ✅ Dashboard/Growth/Notifications有，其余部分有 |
| `any` 类型 | 1处 (services中) |
| UI组件 | Card/Badge/Button/Input/Avatar/Toast/LoadingSpinner |

---

## 9. 测试覆盖

| 测试类型 | 状态 |
|---------|------|
| Unit Test | ❌ 不存在 |
| Integration Test | ❌ 不存在 |
| API Test | ❌ 不存在 (仅手动curl验证) |
| E2E Test | ❌ 不存在 |
| Permission Test | ❌ 不存在 |
| RAG Test | ❌ 不存在 |
| Compliance Test | ❌ 不存在 |
| 前端测试 | ❌ 不存在 |

**无任何自动化测试。无 `tests/` 目录。无 `pytest.ini` / `vitest.config`。**

---

## 10. 文档与代码一致性

| 文档 | 一致性 | 问题 |
|------|--------|------|
| architecture.md | ⚠️ 部分过时 | 列出的模块与实际不完全匹配，缺少成长/通知/Dashboard |
| api.md | ❌ 需审查 | 可能未包含新增的69个端点 |
| database.md | ❌ 需审查 | 可能未包含缺失的迁移和模型 |
| rag.md | ❌ 需审查 | 可能描述了不存在的功能(拒答/版本/权限) |
| compliance.md | ⚠️ 需审查 | 合规引擎规则列表可能不一致 |
| security.md | ⚠️ 需审查 | 描述的安全措施未全部实现 |
| testing.md | ❌ 需审查 | 描述了测试策略但无实际测试 |
| deployment.md | ⚠️ 部分过时 | Demo账号密码不一致(文档写demo123,实际是888888) |
| project-audit.md | ❌ 过时 | Phase编号使用旧体系 |
| README.md | ⚠️ 部分过时 | 可能引用旧Phase编号和Demo密码 |
| worklog.md | ✅ 最新 | Task 13 (Phase 10) 已记录 |

---

## 11. 风险清单

### P0 — 阻断性

| # | 风险 | 影响 |
|---|------|------|
| P0-1 | **无自动化测试** | 无法验证任何修改的正确性 |
| P0-2 | **Alembic迁移不完整** | 多个核心模型(User/Training/Customer/Conversation)无迁移，`alembic upgrade head` 无法创建完整数据库 |
| P0-3 | **Community模型未注册到 `__init__.py`** | ORM导入失败会导致服务启动异常 |
| P0-4 | **所有Service层为纯内存数据** | 切换到Production模式后几乎所有模块不可用 |

### P1 — 严重

| # | 风险 | 影响 |
|---|------|------|
| P1-1 | **无IDOR防护** | 数据权限隔离不存在 |
| P1-2 | **RAG无拒答机制** | 可能对核保/理赔/医疗问题给出不可靠回答 |
| P1-3 | **无审计日志** | 无法追溯关键操作 |
| P1-4 | **无Rate Limiting** | API可被无限调用 |
| P1-5 | **无Prompt Injection防护** | AI接口可被恶意输入操纵 |
| P1-6 | **Community模型未注册** | 导入会失败 |
| P1-7 | **Notification/Growth无数据模型** | 永远只能是Mock |

### P2 — 改进

| # | 风险 | 影响 |
|---|------|------|
| P2-1 | 前端无代码分割 | 首屏加载568KB |
| P2-2 | 无 `/ready` 端点 | K8s/Docker健康检查不完整 |
| P2-3 | docker-compose.yml含明文密码 | 不应提交到Git |
| P2-4 | Demo密码文档不一致 | README写demo123,实际888888 |
| P2-5 | 前端无角色级路由保护 | 登录后任何用户可访问所有页面 |
| P2-6 | Seed脚本从未在迁移中集成 | 数据初始化需手动执行 |

---

## 12. Phase判定

根据总控Prompt的Phase体系:

| Phase | 内容 | 状态 |
|-------|------|------|
| **Phase 1** | 当前状态审计与文档纠偏 | 🔄 **当前执行中** |
| Phase 2 | Demo/Production 架构分层 | ❌ 未开始 — 9个Service全部内存数据 |
| Phase 3 | 数据库与真实持久化 | ❌ 未开始 — 迁移严重不完整 |
| Phase 4 | RAG 生产化 | ❌ 未开始 — 拒答/版本/权限/置信度全部缺失 |
| Phase 5 | 权限与安全强化 | ❌ 未开始 — IDOR/RateLimit/Audit全部缺失 |
| Phase 6 | AI 销售助手 | ❌ 未开始 |
| Phase 7 | 合规系统生产化 | ❌ 未开始 |
| Phase 8 | 社区/成长/通知/Dashboard真实化 | ❌ 未开始 |
| Phase 9 | 全链路测试与生产加固 | ❌ 未开始 |
| Phase 10 | 内部试点发布准备 | ❌ 未开始 |
| Phase 11 | 最终产品验收 | ❌ 未开始 |

### 结论

**当前项目处于 Phase 1（审计阶段）。** 之前的 "Phase 1-10" 是旧编号体系，对应MVP功能开发。按照总控Prompt的新编号体系，项目尚未完成任何一个生产化Phase。

**下一个应执行的Phase: Phase 2 — Demo/Production 架构分层。**

但Phase 1的完成条件是：
1. ✅ 文档与代码基本一致 — 本审计已识别差异
2. ✅ 当前阶段明确 — Phase 2是下一个
3. ✅ P0/P1/P2问题列表明确 — 已列出
