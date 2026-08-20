# 发布就绪基线 — 安诊保 AI 副驾



> 建立时间：2026-08-17

> Git HEAD：`fedc279`（Task 16 校准：GitHub main == origin/main == Release Baseline）

> 项目版本：`0.1.0`（pyproject）

> 判定：**PRODUCTION CANDIDATE**（Task 42 Security Final Review；Accepted Risks 见 §5）



---



## 1. 能力检查表



| 维度 | 状态 | 依据 |

|------|------|------|

| Core Services Production 化 | ✅ | 全部 Service 生产路径闭环（P1-4 已清） |

| 真实 PostgreSQL + pgvector | ✅ | Production Validation + PG 集成测试（含产品边界） |

| 真实 Redis | ✅ | Production Validation |

| 真实 AI Provider（DashScope/Qwen） | ✅ | Real AI Smoke 8/8 PASS（qwen-plus / text-embedding-v3） |

| RAG（向量+BM25+RRF+Confidence Gate+Citation+产品边界+**权限过滤**） | ✅ | Task 12/13 E2E 真实验证 + **Task 17B RAG 权限加固（allowed_roles + 组织范围，SQL WHERE 层；tests/rag/ 35 用例 + PG 权限边界 5 用例）** |

| 安全（JWT/RBAC/限流/消毒/Prompt Injection/**RAG 越权防护**） | ✅ | 单元 + API 集成测试；RAG 权限阻断项已清零（Task 17B） |

| Playwright E2E | ✅ | 阶段一 + 阶段二，11/11 PASS |

| Frontend | ✅ | Vitest **107 passed（16 files）** + Vite build + `tsc -b` 0 errors（Task 32：Admin 8 页面全覆盖 +22 用例；Task 33：全局 ErrorBoundary +4 用例） |

| Backend | ✅ | pytest 全绿（307/68；backend-pg 59 passed，含 Task 27/34/35/37/39/40 各项） |
| Performance（Task 41） | ⚠️ **Cloud CI Capacity Baseline**：基础 API 毫秒级、容量 1-10 并发线性；真实 AI/生产硬件性能 = Not Benchmarked（非 SLA） |

| Docker 部署 | ✅ | 开发 + 生产 compose 均通过 Production Validation |

| 文档一致性 | ✅ | Task 14 全量校准 |



## 2. 已知限制（Known Limitations）



| 项 | 说明 | 影响 |

|----|------|------|

| ~~前端 tsc 硬门禁（P1-6）~~ | **已 RESOLVED（Task 19）**：`tsc -b` 0 errors，CI frontend job 已恢复显式 TypeScript typecheck + `npm run build` 硬门禁 | — |

| growth course_detail（P1-3） | 课程表未落库，生产返回 None | 低（成长模块主链路不受影响） |

| ~~前端组件级测试缺失（P2-3）~~ | **已 RESOLVED（Task 24）**：dashboard/compliance/customers 组件测试 +18 用例（loading/error/empty/mutation/分页），未改生产逻辑 | — |

| ~~Seed 手动执行（P2-4）~~ | **已 RESOLVED（Task 24）**：e2e_seed_knowledge 确定性加固（settings DB URL / embedding fail-fast / 计数不一致 WARN）+ 幂等测试 3 用例 | — |

| ~~CSRF 显式防护（P2-1）~~ | **已收敛（Task 24；Task 34 复核确认已解决，不重复实现）**：Bearer header + 无 cookie → 架构无 CSRF 攻击面（ACCEPTED LIMITATION）；防御性回归测试 4+5 用例（Task 34 新增 TestCsrfSecurityRegression）+ 文档修正 | — |

| ~~Demo 401 语义（P2-2）~~ | **已 RESOLVED（Task 24）**：ErrorHandlerMiddleware 放行 HTTPException（受保护端点认证失败 500→401 真实 bug）、前端 /auth 401 豁免、login 真实错误透传；测试 3 用例 | — |

| ~~无 ErrorBoundary（P2）~~ | **已 RESOLVED（Task 33）**：全局 ErrorBoundary（App.tsx 接线）+ 组件测试 4 用例；任意子树渲染错误降级为可恢复 fallback（重新加载/返回首页） | — |

| ~~上传无大小限制（P2）~~ | **已 RESOLVED（Task 34）**：MAX_UPLOAD_SIZE_MB（默认 10MB）+ Content-Length 预检 + 读取后权威校验 → 413 FILE_TOO_LARGE（demo/production 同享）；测试：demo 分支 413 + PG production 分支 413/200 | — |

| ~~seed 权限绑定丢失 / 版本不一致 / 镜像构建绕过 tsc（P2-4）~~ | **已 RESOLVED（Task 35）**：seed.py 绑定插入补 await（权限关系真正落库，幂等回归测试 3 用例）；APP_VERSION 对齐 0.1.0；frontend/Dockerfile 改 npm run build（对齐 CI 门禁）。详见 docs/deployment-seed-audit.md | — |

| Golden Business Flow | **✅ E2E 验收通过（Task 29）**：浏览器级完整黄金链（登录→Customer360→Agent→RAG/Citation→Compliance→Training→Growth 数据连续），真实 AI provider，27 passed；Real AI phase11 opt-in |
| AI Sales Agent | **后端 + 前端已实现（Task 27/28）** | ToolRegistry + Orchestrator + SSE + RBAC + RAG/Citation + Compliance；前端页面/路由/SSE 流式/Citation/Compliance/REFUSE/错误重试；长期记忆、自动对外销售动作未做（Planned） |
| ~~知识库 CRUD（list/create/update/delete）~~ | **已生产化（Task 21）**：DB backed + 权限继承（org/role/metadata）+ 级联删除 + 同名 409，PG 集成 7 用例（test_kb_crud.py） | — |
| ~~文档管理（list/detail/publish/unpublish/delete）~~ | **已生产化（Task 22）**：DB backed + 继承 KB 权限 + FK CASCADE 无孤儿，PG 集成 7 用例（test_document_management.py） | — |
| ~~Admin 前端 KB/Document 管理~~ | **已生产化（Task 23）**：对接真实 Production API（detail/unpublish/update/404-403 语义/loading 防重复），vitest 13 用例 + E2E K-1~K-3 | — |



## 3. 剩余 P0 / P1 / P2（Task 31 Security Hardening 更新）

- **P0**：无
- **P1**：~~P1-1 KB 上传越权~~ **已修复（Task 31）**：upload_document 补 _can_manage_kb + 回归测试
- **P2**：health/detail 无鉴权（有意开放，compose healthcheck 依赖）、~~上传无大小限制~~ **已收敛（Task 34）**、~~seed 权限绑定/版本一致性/镜像构建一致性~~ **已收敛（Task 35）**、token localStorage、~~AuthGuard 无角色守卫~~（Task 33 复核已解决）、~~无 ErrorBoundary~~ **已收敛（Task 33）**、无环境 badge、Redis no-op

---

### 复核基线（Task 30）



- **P0**：无

- **P1**：~~B1 数据库备份 NOT IMPLEMENTED~~ **已 IMPLEMENTED / CLOUD VERIFIED（Task 38，Pilot 级）**：backup+restore 云端演练全绿（restored==baseline）；正式生产自动调度/对象存储/加密/WAL-PITR 为外部依赖、
  ~~B2 Audit Log 未 DB 持久化~~ **已 RESOLVED（Task 37/37b）**：Repository + 中间件/关键路径落库 + 读端点真实数据 + **组织/角色权限隔离（0010 迁移固化 organization_id）** + 敏感字段不落库（backend-pg 59 passed）、
  P1-3（course_detail Demo Only，低影响）

- **P2**：Redis 化 rate limit/多实例、Agent 内存 session、Demo CORS 放宽、无外部监控告警、
  无滚动部署、Migration 回滚未演练、无额度告警、无性能基准

- **P2**：~~P2-1~P2-4~~ **全部收敛（Task 24）** —— 详见 [p2-hardening-audit.md](p2-hardening-audit.md)



## 4. Verified Facts（当前已验证事实）



```

Real PostgreSQL + pgvector:  PASS

Real Redis:                 PASS

Real DashScope / Qwen:      PASS

Real AI Smoke:              8/8 PASS（phase9/10）；phase11 Golden Flow opt-in（Task 29）

Playwright:                 27/27 PASS（Task 29，含 GF-1 Golden Business Flow）

Production Validation:      PASS（Task 29 最终代码 2f183e3）

Known:                      无 P0；B1/B2 已收敛（Task 37/38 云端验证）；Observability Signals Ready（39）；Redis 多实例共享（40）；Cloud CI 性能基线（41）；Task 42 安全终审升级 **PRODUCTION CANDIDATE**；Accepted Risks：外部告警平台、云托管备份/多地域灾备/Redis HA、滚动发布、渗透测试、localStorage token、上传病毒扫描、演示凭据轮换、真实硬件/真实 AI 性能基准

```



## 5. 发布判定



| 等级 | 说明 | 当前 |

|------|------|------|

| NOT READY | 核心链路未验证 | — |

| READY FOR INTERNAL DEMO | 可演示 | — |

| **PRODUCTION CANDIDATE** | 核心安全与灾备通过（无 P0/无关键越权/B1-B2 云端验证/仓库无 secret）；缺外部监控、云托管备份、多地域灾备、滚动发布、正式渗透测试 = Accepted Risks | ✅ **当前状态（Task 42 Security Final Review）** |

| PRODUCTION READY | 生产上线：需完成 P1/P2 收敛、生产 Secret 管理、安全加固复审 | 未达到 |



> 进入 PRODUCTION READY 前必须：① 恢复前端 tsc 硬门禁；② 收敛 P1/P2；

> ③ 生产部署演练（`scripts/deploy.sh` + `docker-compose.prod.yml`）；④ 安全复审。


## 已知限制（Task 27 新增）

- Agent session 为**进程内内存**（保留最近 8 条消息 + 客户/产品/阶段）：单实例部署可接受；多实例水平扩展时不共享（当前明确标记为限制，不做 silently 依赖）。
- 真实 AI Smoke（phase10）需配置 GitHub Secrets（AZB_AI_API_KEY 等）后手动 workflow_dispatch 触发，普通 CI 默认跳过（避免模型费用）。
