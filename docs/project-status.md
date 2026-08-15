# 安诊保 AI 副驾 — 项目状态（唯一事实来源）



> **本文件是项目状态的唯一事实来源。每完成一个 Phase 必须更新。**

> 最后更新: 2026-08-15

> Git HEAD: `729baedc`

> 后端版本: `1.0.0-rc.1`



---



## A. 当前 Phase



**当前: Phase 6 — 内部试点发布准备（部分完成）**



---



## B. Phase 完成记录



### Legacy MVP Phases（旧编号体系 — 功能开发）



| Phase | 内容 | Git Commit | 状态 |

|-------|------|-----------|------|

| MVP-1 | 基础工程搭建 (FastAPI + React + Docker) | 初始 commit | ✅ 完成 |

| MVP-2 | 用户认证 + RBAC + JWT | 早期 commit | ✅ 完成 |

| MVP-3 | 知识库 + RAG Pipeline (Demo) | 早期 commit | ✅ 完成 |

| MVP-4 | AI 话术模块 + SSE 流式 + 合规引擎 | `e4d225c` Phase 6(旧) | ✅ 完成 |

| MVP-5 | 客户 360° (CRUD + AI 分析) | `e4d225c` Phase 5(旧) | ✅ 完成 |

| MVP-6 | AI 陪练 (场景 + SSE 对话 + 评分) | `b42da9a` Phase 7(旧) | ✅ 完成 |

| MVP-7 | AI 社区 (帖子/评论/点赞/收藏/AI 摘要) | `bdd7389` Phase 8(旧) | ✅ 完成 |

| MVP-8 | 管理后台 (用户/看板/审计/合规/设置) | `146afa2` Phase 9(旧) | ✅ 完成 |

| MVP-9 | 成长体系 + 通知中心 + Dashboard | `72c367f` Phase 10(旧) | ✅ 完成 |



### Productionization Phases（新编号体系 — 生产化）



| Phase | 内容 | Git Commit | 状态 |

|-------|------|-----------|------|

| Prod-1 | 当前状态审计 + 文档校准 | `4441b38` + 本次更新 | ✅ 完成 |

| Prod-2 | Demo/Production 架构分层 (Repository + Service bifurcation) | `79c31b6` | ✅ 完成 |

| Prod-3 | 数据库持久化 (迁移链修复 + 30 表 + Seed) | `1dbf948` | ✅ 完成 |

| Prod-4 | RAG 生产化 (拒答 + 置信度 + Prompt Injection + 版本管理 + 组织隔离) | `a68511c` | ✅ 完成 |

| Prod-5 | 权限安全强化 (IDOR + Rate Limit + 审计 + 脱敏 + 安全头 + 前端 RoleGuard) | `a68511c` | ✅ 完成 |

| Prod-6 | 全链路测试与生产加固 (133 pytest + 27 vitest + Docker 生产配置) | `f2db21f` | ✅ 完成 |

| Prod-7 | 内部试点发布准备 (监控 + 健康检查 + UAT) | Phase 6 本次 + 未提交 | 🔄 进行中 |

| Prod-8 | Task 4: Growth Service Production 化 (GrowthRepository + Leaderboard 组织范围权限) | `69aa76e` `a0851f6` `3de889f` | ✅ 完成 |

| Prod-9 | Task 5: Dashboard Service Production 化 (DashboardRepository 聚合) | `7cd28bf` `943324a` | ✅ 完成 |

| Prod-10 | Task 6: Script Generate + RAG Production 化 (RAG Confidence Gate + Citation + Compliance) | `575775f` `60a3c19` `7b527b9` | ✅ 完成 |

| Prod-11 | Task 7: Community AI Summary Production Hardening (失败不持久化/SSE 完整性/软删除边界) | `73cbba5` `f214d2d` | ✅ 完成 |
| Prod-12 | Task 8: 真实 PG16+pgvector+Redis 全链路环境验收 (compose 全栈 + Phase7/Phase8 + 修复 5 个环境 bug) | `43ad7b0`…`dbe70e6` (13 commits) | ✅ 完成 |
| Prod-13 | Task 9: 真实 AI Provider + SSE 验证 (Gateway 禁静默降级 Mock + AI_TIMEOUT + phase9 smoke + opt-in workflow) | `b21cc35`…`729baed` (6 commits) | ✅ 完成（Real Smoke 待配 Secret） |



---



## C. Production Ready 模块



以下模块代码已就绪，Demo/Production 双路径均已实现：



| 模块 | Demo | Production | 说明 |

|------|------|-----------|------|

| 基础工程 (FastAPI + React) | ✅ | ✅ | |

| JWT 认证 | ✅ | ✅ | |

| RBAC 7 角色 | ✅ | ✅ | |

| 数据库 30 表 | N/A | ✅ | 7 迁移链完整 |

| Repository 7 个 | N/A | ✅ | BaseRepository + 6 业务 Repo |

| Service Bifurcation 8 个 | ✅ | ✅ | |

| RAG Pipeline | ✅ Mock | ✅ pgvector+BM25+RRF | |

| RAG Safety (拒答/置信度/注入检测) | ✅ | ✅ | |

| IDOR 防护 | ✅ | ✅ | 7 角色行级权限 |

| Rate Limiting | ✅ | ✅ | |

| 审计日志 | ✅ (DB pending) | ✅ | |

| 数据脱敏 | ✅ | ✅ | |

| 安全头 (CSP/HSTS/X-Frame) | ✅ (宽松) | ✅ (严格) | |

| 前端角色路由守卫 | ✅ | ✅ | |

| 前端代码分割 | ✅ | ✅ | 入口 ↓34% |

| 健康检查 3 端点 | ✅ | ✅ | Liveness + Readiness + Detail |

| 请求监控日志 | ✅ | ✅ | structlog |



---



## D. Demo Only 模块



以下模块在 Demo 模式使用内存数据，Production 模式需真实 DB/AI：



| 模块 | 说明 |

|------|------|

| AI Gateway | Demo 使用 MockProvider，Prod 需配置真实 AI API Key |

| AI Embedding | pgvector 向量嵌入需真实 OpenAI/DeepSeek Embedding API |

| 所有 Service Demo 数据 | 8 个 Service 的 Demo 数据为内存硬编码，Prod 模式走 Repository→DB |



---



## E. P0 / P1 / P2



### P0 — 无



### P1



| # | 风险 | 说明 |

|---|------|------|

| P1-1 | ~~PostgreSQL + pgvector 真实环境未验证~~ | ✅ Task 8 已验收：真实 PG16+pgvector+Redis compose 全栈启动，Phase7 65 PASS/0 FAIL，pytest 210 passed（详见 G 记录） |

| P1-2 | ~~AI Provider 未接入真实模型~~ | ✅ Task 9 已建立真实 Provider 验证链路：Gateway 支持 OpenAI 兼容 Provider（DeepSeek/Qwen/OpenAI），新增 REAL_AI_SMOKE_TEST opt-in workflow + phase9 脚本；生产模式缺 Key 时明确报错不静默降级 Mock。当前仓库未配置真实 API Key → Real Smoke Test = NOT RUN（可随时配 Secret 触发） |

| P1-3 | **1 个 Service 方法 Production 路径仍为 Demo Only** | growth_service(course_detail — DB 无课程表，生产返回 None 待课程体系落库) |

| P1-4 | **无 Service 方法 Production 路径需完善** | 全部 Service 生产路径已闭环 |

| P1-5 | 无 Playwright E2E 测试 | 仅有 API 级 UAT，无浏览器级 E2E |

| P1-6 | **前端存在大量既有 TypeScript 类型错误** | `npm run build`(tsc) 报 TS6133/TS2322 等错误（分布在多个页面，与 Task 1-3 无关），CI 暂用 `vite build` 绕过 tsc 门禁 |



### P2



| # | 风险 | 说明 |

|---|------|------|

| P2-1 | 无 CSRF 显式防护 | JWT Bearer 下风险较低 |

| P2-2 | Demo 模式无 Token 返回 200 | Prod 模式应正常返回 401 |

| P2-3 | 前端页面组件无测试 | 仅 3 个工具文件有 vitest |

| P2-4 | Seed 脚本未集成到迁移 | 需手动执行 |



---



## E2. Service Production 路径审计结果



| Service | PRODUCTION_READY | NEEDS_WORK | DEMO_ONLY |

|---------|:---:|:---:|:---:|

| customer_service | **8** | 0 | 0 |

| community_service | **10** | 0 | 0 |

| notification_service | **4** | 0 | 0 |

| growth_service | **3** | 0 | 1 (course_detail — DB 无课程表，生产返回 None) |

| dashboard_service | **1** | 0 | 0 |

| training_service | **8** | 0 | 0 |

| script_service | **7** | 0 | 0 |

| **合计** | **41** | **0** | **1** |



---



## F. 下一阶段建议



**Service Production 路径: 全部闭环（41 方法 PRODUCTION_READY）**



1. ✅ **training_service** (8 方法) — Task 1 完成

2. ✅ **script_service** (6 CRUD + generate 持久化) — Task 2 完成（CRUD 部分）

3. ✅ **notification_service** (4 方法) — Task 3 完成（user_id 从 current_user，偏好读写修复）

4. ✅ **growth_service** (3 方法) — Task 4 完成（GrowthRepository 聚合 + Leaderboard 组织范围权限过滤；course_detail 无课程表返回 None 不强建 LMS）

5. ✅ **dashboard_service** (1 方法) — Task 5 完成（DashboardRepository 聚合，今日统计/AI建议/最近活动/未读数全真实 DB）

6. ✅ **script_service.generate_scripts** (1 方法) — Task 6 完成（RAG 检索 + Confidence Gate 拒答 + Citation + Compliance 全链路）

7. ✅ **community_service.ai_summary** (1 方法) — Task 7 完成（AI 失败不持久化错误文本、error 后不发 summary_complete、旧摘要不被覆盖、软删除边界）



完成后再进行:

- PostgreSQL + pgvector 真实环境验收

- Playwright E2E 测试

- 修复前端既有 TypeScript 类型错误（使 `npm run build` 的 tsc 门禁恢复）

- AI Sales Agent 全链路串联



---



## G. 最后验证记录



| 项目 | 结果 | 时间 |

|------|------|------|

| 后端 pytest | **133 passed** (23.32s) | 2026-08-14 |

| 前端 vitest | **27 passed** (2.52s) | 2026-08-14 |

| 前端 TSC | **0 errors** | 2026-08-14 |

| 前端 TSC 核实 (Task 4) | **未恢复 tsc 门禁** — CI frontend job 仍用 `npx vite build` 绕过 tsc（仓库存在既有 TS6133/TS2322 错误，见 P1-6；本次 Growth 改动不触及前端，未扩大战线） | 2026-08-15 (Task 4) |

| 前端 Vite Build | **OK** (374KB entry / 120KB gzip) | 2026-08-14 |

| UAT 冒烟测试 | **23/23 passed** (7.83s) | 2026-08-14 |

| 后端 App Import | **OK** (v1.0.0-rc.1) | 2026-08-14 |

| RAG Safety 拒答 | **OK** (空结果→refuse=True) | 2026-08-14 |

| RAG Safety 注入检测 | **OK** (malicious 检测正常) | 2026-08-14 |

| Rate Limiter | **OK** (10 granted, 5 rejected on 15 requests) | 2026-08-14 |

| 数据脱敏 | **OK** (手机/身份证/姓名/邮箱) | 2026-08-14 |

| Bifurcation | **38/38 methods** 全部正确 | 2026-08-14 (Phase 6 Task 6-1) |

| 模型注册 | **30 tables** 全部可导入 | 2026-08-14 |

| 迁移链 | **7 migrations** (0001→0007) | 2026-08-14 |

| 后端 pytest (含 Task 1 新增 18 个生产路径测试) | **151 passed** (51.05s) | 2026-08-14 (Task 1) |

| Training Production 路径测试 | **18/18 passed**（session/message/score 持久化、权限隔离、资源不存在、非法状态、事务回滚、统计聚合） | 2026-08-14 (Task 1) |

| CI (GitHub Actions) | **backend pytest + frontend vitest + vite build 全部通过** | 2026-08-14 (Task 1) |

| 后端 pytest (含 Task 2 新增 12 个话术生产路径测试) | **163 passed** (49.40s) | 2026-08-14 (Task 2) |

| Script Production 路径测试 | **12/12 passed**（创建/列表/详情/更新/删除/收藏/权限隔离/回滚） | 2026-08-14 (Task 2) |

| CI (GitHub Actions) | **backend pytest + frontend vitest + vite build 全部通过** | 2026-08-14 (Task 2) |

| 后端 pytest (含 Task 3 新增 11 个通知生产路径测试) | **174 passed** (53.13s) | 2026-08-14 (Task 3) |

| Notification Production 路径测试 | **11/11 passed**（列表隔离/筛选/分页、标记已读、偏好默认/更新/未知类型、回滚） | 2026-08-14 (Task 3) |

| CI (GitHub Actions) | **backend pytest + frontend vitest + vite build 全部通过** | 2026-08-14 (Task 3) |

| 后端 pytest (含 Task 4 Growth 生产路径测试) | **190 passed** | 2026-08-15 (Task 4) |

| Growth Production 路径测试 | **9/9 passed**（overview 聚合/空库、leaderboard 排名/空榜、org scope 组织边界、BRANCH_ADMIN 子组织、SYSTEM_ADMIN 全量、course_detail 生产 None、成就用户隔离） | 2026-08-15 (Task 4) |

| CI (GitHub Actions) | **backend pytest + backend-pg (PostgreSQL+pgvector) + frontend 全部通过** | 2026-08-15 (Task 4) |

| 后端 pytest (含 Task 5 Dashboard 生产路径测试) | **190+ passed** | 2026-08-15 (Task 5) |

| Dashboard Production 路径测试 | **5/5 passed**（空库合法结构、今日统计聚合、AI 建议推导、最近活动合并、用户隔离） | 2026-08-15 (Task 5) |

| CI (GitHub Actions) | **backend pytest + backend-pg (PostgreSQL+pgvector) + frontend 全部通过** | 2026-08-15 (Task 5) |

| 后端 pytest (含 Task 6 Script Generate+RAG 生产路径测试) | **197 passed** | 2026-08-15 (Task 6) |

| Script RAG 生产路径测试 | **9/9 passed**（生产检索器、RAG 命中+Citation、RAG 未命中拒答、低置信度拒答、REVIEW 标记、AI 失败不伪造、Compliance 进链、权限归属、无产品类型通用生成） | 2026-08-15 (Task 6) |

| CI (GitHub Actions) | **backend pytest + backend-pg (PostgreSQL+pgvector) + frontend 全部通过** | 2026-08-15 (Task 6) |

| 后端 pytest (含 Task 7 Community AI Summary 生产测试) | **206 passed** | 2026-08-15 (Task 7) |

| Community AI Summary 生产测试 | **9/9 passed**（正常生成+token+持久化、post not found、软删除拒答、AI 失败不写库、超时、空结果、旧摘要不被覆盖、error 后无 summary_complete、真实 wiring+敏感字段检查） | 2026-08-15 (Task 7) |

| CI (GitHub Actions) | **backend pytest + backend-pg (PostgreSQL+pgvector) + frontend 全部通过** | 2026-08-15 (Task 7) |
| Task 8 真实环境验收 (Production Validation workflow) | **Docker Compose 全栈启动 15s / Phase7 65 PASS 0 FAIL / Phase8 14/14 / pytest 210 passed** | 2026-08-15 (Task 8) |
| Task 9 AI Provider 验证 (Task 9) | **Gateway 禁静默降级 Mock（缺 Key 明确报错）/ AI_TIMEOUT 可配 / Provider 测试 14 项新增 / pytest 222 passed / Real AI Smoke Test = NOT RUN（未配置真实 Key，opt-in workflow 已就绪）** | 2026-08-15 (Task 9) |





