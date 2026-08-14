# 安诊保 AI 副驾
# Codex 终极产品收口与生产化总控 Prompt

你现在负责继续开发：

> **安诊保 AI 副驾**

这是一个面向保险代理人的企业级 AI 销售赋能平台。

当前项目已经完成大量 MVP 功能，包括但不限于：

- 登录与 RBAC
- 工作台
- AI 产品问答
- RAG / 知识库
- 客户 360
- AI 客户分析
- AI 话术
- 合规引擎
- AI 陪练
- AI 社区
- 管理后台
- 成长体系
- 通知中心
- Dashboard

现在项目不再以“增加功能数量”为主要目标。

新的最高目标是：

> **把当前功能丰富的 MVP，真正收口为一个稳定、可维护、可测试、可审计、可内部试点的企业级 AI 产品。**

---

# 0. 最高优先级项目原则

你必须始终遵守：

> **少堆功能，多做闭环。**

> **少做 Demo，多做真实持久化。**

> **少做视觉装饰，多做业务可靠性。**

> **少做单点 AI，多做 AI 工作流。**

最终目标不是：

> GitHub 上“看起来很完整”。

而是：

> 一个真实代理人能够每天使用它完成销售准备、客户分析、话术生成、合规检查和能力训练。

---

# 1. 产品核心闭环

最终必须形成：

```text
客户
 ↓
客户 360
 ↓
AI 客户分析
 ↓
产品知识检索
 ↓
销售策略
 ↓
AI 话术
 ↓
合规检查
 ↓
人工确认
 ↓
AI 陪练
 ↓
训练结果
 ↓
能力成长
 ↓
经验沉淀
 ↓
知识库
 ↓
RAG
```

这是整个产品的核心业务闭环。

---

# 2. 产品核心原则

## AI 是副驾

AI 可以：

- 查询
- 分析
- 推荐
- 生成
- 训练
- 复盘

AI 不可以直接：

- 修改真实客户核心事实
- 修改保单
- 修改真实核保结论
- 修改真实理赔结论
- 自动向客户发送高风险内容

高风险操作必须人工确认。

---

# 3. 业务来源

《安诊保-AI赋能.pdf》是本项目核心业务背景依据。

其中确定：

- 第一阶段重点为“代理人 AI 副驾 + 内部 AI 社区”
- 产品问答必须基于 RAG
- 回答需要带出处
- 不确定时拒答
- 数据需要权限隔离
- 对客关键内容先审后发
- 先通过 MVP 进行小范围试点

不要擅自发明真实保险条款、真实核保规则、真实理赔规则。

缺少真实业务依据时：

> 使用 Demo / Mock / 待确认。

---

# 4. 极其重要：分阶段执行规则

你必须严格按照以下 Phase 执行：

```text
Phase 1
↓
测试
↓
修复
↓
汇报

Phase 2
↓
测试
↓
修复
↓
汇报

……
```

## 不允许一次性执行全部 Phase。

每次启动任务时：

1. 查看当前 Git 状态；
2. 查看 worklog；
3. 查看 docs/current-state；
4. 判断当前完成到哪个 Phase；
5. **只执行下一个未完成 Phase。**

---

# 5. Phase 1
# 当前状态审计与文档纠偏

目标：

> 建立项目当前真实状态。

首先扫描：

```text
README.md
worklog.md
docs/
frontend/
backend/
docker-compose.yml
.env.example
.gitignore
```

检查：

- 当前技术栈
- 当前 Git HEAD
- 当前 API
- 当前数据库
- 当前 Repository
- 当前 Mock
- 当前 Demo 数据
- 当前 RAG
- 当前权限
- 当前测试

创建：

```text
docs/current-state-audit.md
```

必须列出：

```text
已完成
部分完成
Demo
Mock
Production
P0风险
P1风险
P2风险
```

同时更新所有过时文档。

尤其是：

```text
project-audit.md
README.md
worklog.md
database.md
api.md
rag.md
ai-agents.md
compliance.md
security.md
testing.md
```

要求：

> 文档不能描述与当前代码相反的状态。

### Phase 1 完成条件

- 文档与代码基本一致
- 当前阶段明确
- P0/P1/P2 问题列表明确

完成以后停止。

---

# 6. Phase 2
# Demo / Production 架构分层

目标：

> 清理 Demo 逻辑，让核心业务具备生产化结构。

检查所有：

```text
Customer
Script
Training
Community
Growth
Notification
Knowledge
Admin
```

识别：

```text
hardcoded data
in-memory data
mock repository
demo repository
```

统一为：

```text
Router
 ↓
Service
 ↓
Repository / Adapter
 ↓
Data Source
```

例如：

```text
CustomerRepository
├── DemoCustomerRepository
└── PostgresCustomerRepository
```

不要大量使用：

```python
if demo_mode:
```

污染业务层。

### Phase 2 完成条件

Demo 模式与 Production 模式逻辑边界清晰。

---

# 7. Phase 3
# 数据库与真实持久化

审查当前：

```text
users
roles
permissions
organizations

customers
customer_interactions
customer_followups

products
product_versions

documents
document_versions
document_chunks

conversations
messages

scripts
script_versions

training_scenarios
training_sessions
training_scores

community_posts
community_comments
community_likes

compliance_rules
compliance_reviews

ai_requests
ai_feedback

notifications

audit_logs
```

确保：

- 主键
- 外键
- 唯一约束
- 索引
- 时间字段
- 状态字段
- 版本字段
- 组织范围
- 用户范围

全部合理。

尤其明确：

```text
customer fact
```

和：

```text
AI inference
```

必须分离。

### Phase 3 完成条件

核心业务模块能够真正使用 PostgreSQL 持久化。

---

# 8. Phase 4
# RAG 生产化

建立完整链路：

```text
Document
 ↓
Parse
 ↓
Normalize
 ↓
Chunk
 ↓
Metadata
 ↓
Embedding
 ↓
Vector Search
 +
BM25
 ↓
Hybrid Search
 ↓
RRF
 ↓
Rerank
 ↓
Permission Filter
 ↓
Confidence Gate
 ↓
LLM
 ↓
Citation
 ↓
Compliance
 ↓
Answer
```

---

## RAG 硬规则

如果没有足够知识依据：

> 必须拒答。

禁止：

> “基于通用保险知识回答”。

尤其：

- 核保
- 理赔
- 健康告知
- 免责
- 责任
- 赔付
- 医疗结论

全部遵循：

```text
知识库有依据
→ 回答

知识库没有足够依据
→ 拒答 / 转人工
```

---

## RAG 必须支持

- 文档版本
- 生效日期
- 失效日期
- 来源
- 章节
- 页码
- 权限
- 风险级别
- 引用原文

### Phase 4 完成条件

自动测试必须验证：

- 正确检索
- 无结果拒答
- 版本正确
- 引用正确
- 权限正确
- Prompt Injection 无法绕过

---

# 9. Phase 5
# 权限与安全强化

必须全面检查：

```text
JWT
RBAC
IDOR
SQL Injection
XSS
CSRF
Rate Limit
File Upload
Prompt Injection
RAG 越权
敏感数据泄露
Secret 泄露
日志泄露
```

重点保证：

```text
Agent A
不能访问
Agent B 客户
```

不仅前端不能看到。

后端 API 也必须拒绝。

RAG 也必须拒绝。

---

## Secrets

确保：

```text
.env
.env.local
API KEY
JWT SECRET
DB PASSWORD
```

不能进入 Git。

只保留：

```text
.env.example
```

Demo 密码明确：

> DEMO ONLY / NON-PRODUCTION

### Phase 5 完成条件

权限测试和安全测试通过。

---

# 10. Phase 6
# AI 销售助手

这是当前最重要的新能力。

在客户 360 中增加：

> AI 销售助手。

它不是聊天窗口，而是 Agent。

---

## Agent 能力

```text
Customer Tool
Knowledge Tool
Script Tool
Compliance Tool
Training Tool
```

流程：

```text
客户事实
 ↓
历史沟通
 ↓
销售阶段
 ↓
AI分析
 ↓
产品知识
 ↓
销售策略
 ↓
生成话术
 ↓
合规检查
 ↓
下一步动作
 ↓
陪练
```

---

## 页面应该体现

```text
当前销售阶段

AI判断

客户关注点

推荐策略

推荐话术

合规结果

推荐行动

[复制话术]

[重新生成]

[开始陪练]
```

### Agent 安全边界

可以：

- 查询
- 分析
- 生成
- 推荐
- 创建草稿

不可以：

- 修改核心客户事实
- 发送客户消息
- 修改真实保险业务结论

### Phase 6 完成条件

一个真实 Demo 客户可以跑完整条 AI 销售助手流程。

---

# 11. Phase 7
# 合规系统生产化

当前已有：

```text
GREEN
YELLOW
RED
```

继续保留。

统一返回：

```json
{
  "status": "",
  "score": 0,
  "violations": [],
  "suggestions": [],
  "can_send": false,
  "review_required": false
}
```

完整链路：

```text
AI生成
 ↓
Compliance
 ↓
GREEN/YELLOW/RED
 ↓
修改
 ↓
再次检查
 ↓
人工确认
```

禁止：

```text
AI
 ↓
直接发送客户
```

---

## 审计

每一次关键合规行为记录：

- user
- content hash
- rule version
- violations
- result
- timestamp
- reviewer
- final action

### Phase 7 完成条件

RED 无法通过前端绕过。

YELLOW 必须人工确认。

GREEN 可以进入下一步。

---

# 12. Phase 8
# 社区、成长、通知、Dashboard 真实化

逐步把当前 Demo 内存数据迁移到 PostgreSQL。

优先：

```text
Knowledge
Compliance
Audit
Community
Notification
Growth
Dashboard
```

---

## 社区

形成：

```text
案例
 ↓
AI总结
 ↓
管理员审核
 ↓
知识
 ↓
知识库
```

最终形成：

> 经验 → 企业知识 → RAG。

---

## 成长

训练数据必须真正来自：

```text
training_sessions
training_scores
```

不要硬编码：

```text
87分
42积分
```

---

## Dashboard

尽量使用真实数据库数据。

如果仍然是 Mock：

必须明确显示：

> Demo Data

禁止伪造业务收益。

### Phase 8 完成条件

主要外围模块不再依赖大量内存 Demo 数据。

---

# 13. Phase 9
# 全链路测试与生产加固

至少实现：

## E2E 1

```text
登录
→ 工作台
→ 客户
→ AI分析
→ 产品查询
→ 话术
→ 合规
→ 陪练
→ 成长
```

## E2E 2

```text
AI问答
→ RAG命中
→ 显示引用
```

## E2E 3

```text
AI问答
→ RAG无结果
→ 拒答
```

## E2E 4

```text
Agent A
→ 尝试访问 Agent B 客户
→ 403/404
```

## E2E 5

```text
高风险话术
→ RED
→ 禁止发送
```

## E2E 6

```text
社区案例
→ AI总结
→ 审核
→ 知识
```

---

# 14. 测试类型

最终至少：

```text
Unit
Integration
API
Permission
RAG
Compliance
E2E
```

覆盖：

- 正常
- 空数据
- 错误
- 超时
- AI失败
- 数据库失败
- 权限不足
- RAG无结果
- Prompt Injection
- 重复提交

---

# 15. Phase 10
# 内部试点发布准备

最终目标：

> 可以交给一小批真实代理人进行内部试点。

必须完成：

```text
Docker
Health Check
.env.example
Database migration
Seed data
Demo mode
Production mode
Logging
Audit
Monitoring
Release Checklist
README
```

提供：

```text
GET /health
GET /ready
```

---

# 16. Pilot Mode

支持：

```text
PILOT_MODE=true
```

允许限定：

```text
组织
分公司
团队
代理人
```

避免第一阶段全员开放。

---

# 17. 试点指标

系统需要记录：

```text
DAU
WAU
AI问答
答案采纳
话术生成
话术复制
陪练次数
陪练完成率
RAG命中率
RAG拒答率
合规拦截率
社区活跃度
```

不要在没有真实实验结果时宣称：

> 转化率提升 X%。

---

# 18. Phase 11
# 最终产品验收

使用以下六种角色进行验收：

```text
代理人
团队主管
知识管理员
合规人员
管理员
技术人员
```

分别验证：

### 代理人

能否完成一次完整销售准备？

### 主管

能否看到团队能力和使用情况？

### 知识管理员

能否控制知识来源与版本？

### 合规

能否审计 AI 输出？

### 管理员

能否管理组织和用户？

### 技术人员

能否部署、运行、定位问题？

---

# 19. 最终业务闭环验收

必须成功完成：

```text
登录
 ↓
工作台
 ↓
客户360
 ↓
AI销售助手
 ↓
客户分析
 ↓
产品知识
 ↓
AI话术
 ↓
合规检查
 ↓
人工确认
 ↓
AI陪练
 ↓
评分
 ↓
成长
```

---

# 20. 最终技术验收

必须通过：

```text
Build
Lint
Typecheck
Unit Test
Integration Test
E2E
Permission Test
RAG Test
Compliance Test
Security Review
Docker Build
Health Check
```

---

# 21. 最终代码质量

禁止：

- 大量 any
- 巨型组件
- 巨型 Router
- 重复代码
- Secret 硬编码
- 无意义 TODO
- 无后端的假页面
- 随机数 KPI
- setTimeout 假接口
- 前端权限代替后端权限

---

# 22. UI 最终要求

现在不要继续增加大量视觉效果。

优先保证：

- 信息层级
- Loading
- Empty
- Error
- Skeleton
- Permission
- Retry
- 操作反馈
- 响应式
- 统一 Design System

整体保持：

> 企业级金融科技 + AI Native + 专业克制。

---

# 23. 最终 Git 策略

按照功能提交：

```text
feat:
fix:
refactor:
security:
test:
docs:
```

不要一次性提交大量无关修改。

---

# 24. 每个 Phase 必须自动做的事情

完成当前 Phase 后：

```text
1. 运行测试
2. 运行 Build
3. 修复错误
4. 再次测试
5. 更新 docs
6. 更新 worklog
7. 更新 decisions
8. 检查 Git diff
9. 检查是否产生 Secret
10. 输出本 Phase 汇报
```

---

# 25. Phase 汇报格式

每个阶段完成后只汇报：

```text
当前 Phase：

完成内容：

修改文件：

数据库变化：

API变化：

测试结果：

发现的问题：

仍存在的 P0：

仍存在的 P1：

下一阶段：
```

不要在 Phase 未完成时宣布项目完成。

---

# 26. 自动选择当前 Phase

每次运行本 Prompt：

首先判断：

```text
当前仓库完成到哪个 Phase
```

例如：

```text
Phase 1 完成
Phase 2 未完成
```

那么：

> 只执行 Phase 2。

不要重新执行 Phase 1。

如果某个 Phase 已经部分完成：

> 审计现状后，只补缺失部分。

不要重复重写。

---

# 27. 最重要的一条

如果已经存在可用实现：

> **优先修复和增强，而不是重写。**

除非现有架构已经明显阻碍后续开发。

---

# 28. 当前阶段的最终目标

最终把项目从：

```text
功能丰富的 MVP
```

变成：

```text
真正可内部试点的 AI 销售副驾
```

最终产品应该成为：

```text
             安诊保 AI 副驾
                    │
      ┌─────────────┼─────────────┐
      ↓             ↓             ↓
    工作台        客户360        AI中心
                    │
                    ↓
               AI销售助手
                    │
          ┌─────────┼─────────┐
          ↓         ↓         ↓
        知识       话术       陪练
          │         │         │
          └─────────┼─────────┘
                    ↓
                  合规
                    ↓
                 人工确认
                    ↓
                 业务行动
                    ↓
                  数据
                    ↓
               经验沉淀
                    ↓
                  知识库
                    ↓
                   RAG
```

最终形成：

> **知识 → AI → 客户 → 销售 → 合规 → 训练 → 经验 → 知识**

的数据飞轮。

---

# 29. 最终停止条件

当且仅当满足：

```text
核心业务真实持久化
RAG 可靠
权限可靠
合规可靠
AI Sales Agent 可用
核心业务闭环跑通
E2E 通过
安全测试通过
Docker 可部署
文档同步
```

才可以宣布：

# MVP READY FOR INTERNAL PILOT

---

# 30. 现在开始

现在不要继续讨论。

先：

> 审计当前项目。

然后：

> 自动判断当前未完成的最早 Phase。

然后：

> **只执行这个 Phase。**

完成以后：

> 测试 → 修复 → 汇报。

不要一次执行全部 Phase。

不要因为 Prompt 很长而提前实现后续阶段。

**逐项执行，逐项验收，逐项推进。**