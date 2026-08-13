# 安诊保 AI 副驾｜Codex 0→1 产品研发总控 Prompt

你现在不是在“帮我写几个页面”，而是在负责从 0 到 1 构建一个可以真实运行、可以进行内部试点、可以持续迭代的企业级 AI 产品。

项目名称：

**安诊保 AI 副驾**

产品定位：

> 面向华安保险一线代理人的 AI 销售赋能工作台，把“产品知识、客户理解、销售准备、话术生成、AI 陪练、业务复盘、经验沉淀”串成一个完整闭环。

本项目的业务背景、产品范围和核心功能，以我提供的《安诊保-AI赋能.pdf》为最高优先级业务依据。不要擅自改变其中已经确定的业务定位、产品名称、核心逻辑和优先级。

PPT 中明确提出第一阶段优先建设：

- 代理人 AI 副驾
- 内部 AI 社区

并以 3 个月 MVP 为第一阶段目标，再逐步扩展客户助手、智能核保/理赔、AI 精算等能力。

---

# 一、你的总任务

请直接把本项目开发成一个**可运行的完整 Web 产品 MVP**，而不是做一个静态 Demo。

最终必须具备：

1. 真实前端页面
2. 真实后端 API
3. 真实数据库
4. 用户认证
5. RBAC 权限体系
6. AI 调用抽象层
7. RAG 知识库
8. AI 产品问答
9. AI 话术生成
10. AI 陪练
11. 客户 360
12. AI 社区
13. 管理后台
14. 知识库管理
15. 合规审核
16. 操作审计
17. 埋点与数据统计
18. Mock 数据
19. Demo 模式
20. Docker 本地启动
21. 完整 README
22. 测试
23. 可扩展架构

不要为了“看起来完成了”而用大量假数据拼 UI。

可以有 Demo / Mock 模式，但必须通过清晰的 Service / Repository / Adapter 层隔离，未来能够无痛切换到真实数据库、真实模型 API 和真实企业微信。

---

# 二、最重要的开发原则

## 原则 1：先产品，再代码

不要一上来疯狂写 React 页面。

第一步先：

1. 分析需求
2. 识别用户角色
3. 建立信息架构
4. 建立用户流程
5. 建立数据模型
6. 建立 API Contract
7. 再实现页面
8. 再实现 AI
9. 最后做联调与测试

如果仓库已经存在代码，请先理解现有代码，再决定修改方案。

不要无脑重构现有项目。

---

# 三、产品核心闭环

整个产品必须围绕下面这个闭环设计：

```text
产品知识库
    ↓
AI 产品专家
    ↓
客户 360
    ↓
AI 销售 Agent
    ↓
话术生成
    ↓
AI 陪练
    ↓
真实销售
    ↓
成交 / 拒绝 / 跟进
    ↓
AI 复盘
    ↓
AI 社区
    ↓
经验沉淀
    ↓
知识库升级
    ↓
AI 能力持续增强
```

不要把产品做成：

> “一个企业聊天机器人 + 几个孤立工具”。

它必须体现出“AI 代理人工作台”的产品属性。

---

# 四、第一版功能边界

第一版必须完成下面这些模块：

## A. 登录 / 身份体系

支持：

- 手机号登录 Demo
- 企业账号登录抽象
- 用户身份
- 用户角色
- 用户所属机构
- 用户所属团队

角色至少包括：

```text
AGENT             代理人
TEAM_LEADER       团队主管
BRANCH_ADMIN      分公司管理员
HQ_ADMIN          总部管理员
KNOWLEDGE_ADMIN   知识库管理员
COMPLIANCE        合规人员
SYSTEM_ADMIN      系统管理员
```

使用 RBAC。

所有后端接口都必须做服务端鉴权。

不要只在前端隐藏菜单。

---

# 五、信息架构

产品一级导航设计为：

```text
工作台
AI产品专家
客户360
AI话术
AI陪练
AI社区
我的成长
消息中心

管理后台
├── 用户管理
├── 客户管理
├── 知识库
├── 陪练场景
├── 话术库
├── 社区管理
├── 合规中心
├── 数据看板
├── 审计日志
└── 系统设置
```

普通代理人看不到管理后台。

---

# 六、整体 UI/UX 要求

整体视觉：

> 企业级金融科技 + 现代 AI 产品 + 克制高级感

不要做成：

- 花哨互联网营销页
- 二次元
- 纯聊天软件
- 低级 SaaS 模板
- 大量渐变
- 大量装饰性动画

整体要求：

- 清晰
- 专业
- 高级
- 稳重
- 现代
- 信息密度合理
- 长期使用不疲劳

建议整体采用：

```text
左侧：
一级导航

顶部：
搜索 / AI快捷入口 / 消息 / 用户

中部：
核心工作区

右侧：
AI上下文辅助区域（必要页面才出现）
```

支持：

- PC 优先
- 平板适配
- 移动端基础响应式
- 深色模式架构预留

但第一版不要为了移动端牺牲桌面端体验。

---

# 七、首页：代理人工作台

这是最重要的页面之一。

不要直接做聊天框首页。

首页需要体现：

> “AI 正在帮助代理人工作”。

布局建议：

```text
顶部
“早上好，XXX”

AI 总入口
“今天有什么需要帮忙？”

快捷操作：
[问产品]
[分析客户]
[生成话术]
[开始陪练]

---

今日工作

待跟进客户
待回复客户
今日陪练
知识更新

---

AI 今日建议

客户 A
高意向
建议今天 18:30 触达

客户 B
刚完成复诊
适合进入慢病版沟通

---

最近使用

最近问答
最近话术
最近陪练
```

所有卡片都必须是真正可点击进入对应功能。

---

# 八、AI 产品专家

这是第一优先级功能。

目标：

> 帮代理人快速回答产品、条款、服务、销售规则相关问题。

PPT明确要求：

> 产品问答强制采用 RAG，回答必须带出处，检索不到时直接拒答。

## 页面要求

提供类似现代 AI Copilot 的聊天界面，但不要复制 ChatGPT UI。

顶部：

```text
AI 产品专家
已连接：安诊保知识库
```

用户可以：

```text
输入问题
上传文件
选择产品
选择知识范围
查看历史对话
```

回答必须支持：

```text
结论
关键依据
条款出处
来源文档
页码
风险提示
```

示例：

```text
结论

根据当前知识库，暂无法直接判断该客户是否符合承保条件。

依据

《安诊保慢病版产品条款》
健康告知
第 XX 页

建议进一步确认：

1. 最近一次测量值
2. 是否长期用药
3. 是否存在并发症

风险提示：

该回答仅用于代理人业务辅助，不构成最终核保结论。
```

必须支持：

- 查看来源
- 查看原文
- 复制答案
- 转为销售话术
- 收藏
- 点赞 / 点踩
- “答案有误”
- 反馈原因

---

# 九、RAG 系统

实现真实 RAG 架构。

推荐：

```text
文档上传
↓
解析
↓
结构化
↓
Chunk
↓
Embedding
↓
向量数据库
↓
BM25
↓
Hybrid Search
↓
Rerank
↓
权限过滤
↓
LLM
↓
引用
↓
合规检查
↓
结果
```

不要只做：

```text
PDF → embedding → similarity → GPT
```

需要 Metadata。

示例：

```json
{
  "product": "安诊保慢病版",
  "document_name": "产品条款",
  "version": "2026-v1",
  "section": "健康告知",
  "page": 5,
  "effective_date": "2026-08-01",
  "permission": "AGENT",
  "risk_level": "HIGH"
}
```

知识库必须支持：

- 文档版本
- 生效日期
- 失效日期
- 文档类型
- 产品
- 来源
- 上传人
- 审核状态
- 发布状态
- 权限
- 风险等级

知识版本必须可追踪。

如果一个新版本发布：

旧版本不能继续作为默认回答依据。

---

# 十、知识库管理后台

管理员可以：

```text
上传文件
查看文档
预览文档
解析
重新切片
重新向量化
查看 Chunk
修改 Metadata
提交审核
审核
发布
下线
版本管理
```

知识生命周期：

```text
上传
→ 解析
→ 草稿
→ 审核
→ 发布
→ 生效
→ 失效
```

管理员能够查看：

```text
文档名称
版本
发布时间
生效时间
Chunk数量
召回次数
使用次数
错误反馈次数
```

---

# 十一、AI 话术助手

这个模块不能只是：

> 输入问题 → 大模型输出一段文字。

必须做成真正销售辅助工具。

输入方式：

```text
选择客户
+
客户当前状态
+
客户异议
+
销售阶段
```

例如：

```text
客户：陈先生
年龄：52
类型：慢病
状态：已沟通两次
当前异议：贵
```

点击：

> 生成话术

自动生成：

```text
亲和型
专业型
数据型
简洁型
```

每条话术：

- 可复制
- 可编辑
- 重新生成
- 查看依据
- 合规检查

---

# 十二、合规检查

所有面向客户的 AI 话术必须通过 Compliance Engine。

建立规则：

```text
收益承诺
绝对化表达
虚假比较
夸大保障
不当核保结论
不当理赔承诺
诱导销售
敏感医疗结论
```

输出：

```text
GREEN
可以使用

YELLOW
建议人工修改

RED
禁止发送
```

示例：

```text
风险等级：YELLOW

问题：
包含“肯定可以赔”类似绝对化表述。

建议：
修改为“具体以保险合同及实际理赔审核结果为准”。
```

注意：

AI 只是辅助。

最终客户沟通必须由代理人确认。

PPT已经明确提出“对客先审后发”。

---

# 十三、客户 360

建立客户列表。

字段：

```text
姓名
年龄
客户类型
客户标签
产品
当前阶段
意向度
最后联系时间
下次跟进时间
负责人
```

客户详情页面：

```text
基本资料

客户画像

健康相关信息（权限控制）

沟通记录

购买记录

跟进记录

AI分析

AI建议

历史话术

陪练记录
```

AI 自动生成：

```text
客户类型
购买意向
价格敏感度
服务敏感度
推荐产品
推荐沟通方向
最佳跟进时间
沟通禁区
```

但所有 AI 推断必须明确标注：

> AI分析 / 仅供业务辅助

不要把模型推断伪装成真实客户事实。

---

# 十四、AI 销售 Agent

这是整个产品后期的核心能力。

用户可以输入：

> “帮我分析陈先生今天应该怎么跟进。”

Agent 自动：

```text
查询客户
→ 获取历史沟通
→ 获取产品
→ 查询知识
→ 分析销售阶段
→ 生成策略
→ 生成话术
→ 合规检查
```

最后给出：

```text
今日建议

优先级：★★★★★

原因：

客户3天未跟进
近期主动咨询慢病版
价格异议已处理过一次

推荐行动：

今天18:30-20:00再次触达

推荐话术：

……

不要做：

不要再次直接强调价格
不要做承保承诺
不要制造焦虑
```

---

# 十五、AI 陪练

必须做成真正的互动式训练，而不是固定问答。

流程：

```text
选择场景
↓
选择难度
↓
AI扮演客户
↓
用户回答
↓
AI继续追问
↓
完成
↓
评分
↓
总结
↓
生成训练建议
```

第一版至少做：

```text
价格异议
“没必要”
“太贵”
“网上更便宜”
“考虑一下”
“先不买”
“身体挺好的”
“以前买过保险”
慢病客户
老年客户
家庭客户
子女替父母投保
```

不少于 20 个场景。

---

# 十六、陪练评分模型

至少三个维度：

```text
产品准确性
客户共情
促单动作
```

最终：

```text
总分

优势：

问题：

建议：

下一次训练：

推荐话术：
```

支持：

- 历史成绩
- 成绩趋势
- 场景掌握度
- 能力雷达图
- 个人成长记录

不要把分数直接和现实绩效绑定。

第一版只做成长能力指标。

---

# 十七、AI 社区

AI 社区不能设计成普通论坛。

定位：

> 企业 AI 知识中枢。

功能：

```text
业务问答
案例复盘
优秀话术
培训内容
新人学习
政策通知
产品更新
```

首页：

```text
今日热门问题

优秀案例

销冠经验

产品更新

今日训练

AI推荐
```

任何用户都可以：

```text
提问
回答
点赞
收藏
评论
```

AI 自动：

```text
提炼答案
提炼案例
提炼话术
提炼知识点
```

但：

> AI 自动生成的公司级知识必须进入人工审核流程。

审核后才可以进入正式知识库。

---

# 十八、经验沉淀闭环

实现：

```text
优秀问答
↓
AI总结
↓
审核
↓
标准知识
↓
知识库
```

以及：

```text
优秀陪练
↓
AI总结
↓
审核
↓
优秀话术
↓
话术库
```

以及：

```text
真实案例
↓
AI复盘
↓
经验卡片
↓
AI社区
```

最终形成：

> 个人经验 → 团队经验 → 公司知识资产。

---

# 十九、消息中心

实现：

- 新客户
- AI推荐任务
- 陪练提醒
- 知识更新
- 系统公告
- 审核通知
- 社区互动

消息支持：

```text
未读
已读
全部已读
跳转
```

---

# 二十、我的成长

代理人可以看到：

```text
AI使用次数
问答次数
话术生成次数
陪练次数
陪练成绩
常见错误
成长趋势
擅长场景
待提升场景
```

最终形成：

> AI 销售能力画像。

---

# 二十一、管理后台

管理后台必须是真正可用的。

## 用户管理

支持：

- 查询
- 筛选
- 新建
- 编辑
- 禁用
- 重置
- 角色
- 所属组织

## 组织管理

```text
总部
 ↓
分公司
 ↓
团队
 ↓
代理人
```

## 客户管理

支持：

- 查询
- 标签
- 分配
- 跟进
- 状态
- 数据导出权限控制

## 知识库

前面已经详细定义。

## 陪练场景

管理员可以：

```text
新增场景
编辑场景
删除
发布
下线
修改客户人格
修改难度
修改评分规则
```

## 话术库

支持：

```text
新增
审核
发布
收藏
评价
版本
```

---

# 二十二、合规中心

建立统一审计中心。

记录：

```text
谁
什么时候
访问什么
问了什么
AI回答什么
依据是什么
是否命中风险
谁审核
最终是否发送
```

所有关键动作进入 Audit Log。

日志必须不可由普通用户删除。

---

# 二十三、数据看板

后台增加：

```text
DAU
WAU
AI问答量
回答采纳率
话术生成量
陪练次数
社区活跃度
知识库使用率
高风险回答数
合规拦截数
```

销售业务指标预留：

```text
人均产能
成交件数
转化率
续保率
```

不要在没有真实数据时伪造“AI提升了25%”之类的业务结论。

Demo 页面可以展示 Mock 数据，但明确标注：

> Demo Data

---

# 二十四、数据库

如果技术栈没有特别约束，默认：

```text
PostgreSQL
Redis
Vector DB
Object Storage
```

核心表至少包括：

```text
users
roles
permissions
organizations

customers
customer_tags
customer_interactions
customer_followups

products
product_versions

documents
document_versions
document_chunks
knowledge_permissions

conversations
messages

scripts
script_versions

training_scenarios
training_sessions
training_messages
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

system_configs
```

数据库设计必须规范化。

不要把所有数据塞进 JSON。

JSON 只在适合的地方使用。

---

# 二十五、AI Gateway

业务层禁止直接写：

```python
openai.chat.completions.create(...)
```

必须建立统一抽象：

```text
AIProvider
├── OpenAICompatibleProvider
├── DeepSeekProvider
├── QwenProvider
├── MockProvider
```

业务层：

```text
AIService
    ↓
AI Gateway
    ↓
Provider
```

支持模型切换。

例如：

```text
deepseek
qwen
openai-compatible
mock
```

配置全部环境变量化。

不要把 API Key 写死。

---

# 二十六、Prompt 管理

所有核心 Prompt 不允许散落在代码里面。

统一：

```text
/prompts
    product_qa/
    script_generation/
    customer_analysis/
    roleplay/
    compliance/
    summarization/
```

每个 Prompt：

```text
system prompt
version
description
variables
expected output
risk level
```

支持版本管理。

---

# 二十七、AI 输出必须结构化

能结构化就不要依赖纯字符串。

例如客户分析：

```json
{
  "customer_type": "",
  "purchase_intent": 0,
  "price_sensitivity": "",
  "recommended_product": "",
  "recommended_actions": [],
  "forbidden_actions": [],
  "risk_notes": []
}
```

陪练评分：

```json
{
  "total_score": 0,
  "product_accuracy": 0,
  "empathy": 0,
  "closing_action": 0,
  "strengths": [],
  "weaknesses": [],
  "recommendations": []
}
```

这样前端才能真正稳定渲染。

---

# 二十八、安全设计

必须考虑：

```text
身份认证
RBAC
CSRF
XSS
SQL注入
Rate Limit
API鉴权
敏感数据脱敏
日志审计
文件上传安全
Prompt Injection
RAG越权
模型输出安全
```

尤其处理文档时：

> 用户上传的文档不能通过 Prompt Injection 控制系统行为。

知识库内容永远是：

> 数据

不是：

> 系统指令。

---

# 二十九、客户数据安全

客户隐私必须做到：

```text
数据库权限隔离
接口权限检查
字段级权限
日志审计
脱敏
最小权限
```

例如：

普通代理人不能看到：

> 其他代理人的客户。

团队主管可以：

> 查看团队客户。

总部管理员可以：

> 查看聚合数据。

系统管理员：

> 默认不应获得业务明文数据权限，遵循最小权限原则。

---

# 三十、Mock 模式

由于真实企业系统和真实 API 暂时可能不可用，必须支持：

```text
DEMO_MODE=true
```

开启以后：

- 登录直接使用 Demo 用户
- AI 使用 MockProvider
- 数据库使用 Seed 数据
- RAG 使用 Demo 知识
- 所有功能仍然可以完整演示

Demo 页面不能出现：

> “功能开发中”

而应该完整跑通业务流程。

---

# 三十一、种子数据

必须创建一套完整 Demo 数据：

至少：

```text
10名代理人
2名主管
1个分公司管理员
20名客户
2个产品
30篇知识文档/知识条目
20+陪练场景
30条优秀话术
30条社区内容
20条跟进记录
50条AI操作记录
```

创建真实感强的中文业务数据。

不要使用：

```text
test
abc
123
张三
李四
```

这种明显占位数据。

---

# 三十二、API 设计

REST API 为主。

例如：

```text
POST /api/auth/login

GET /api/dashboard

POST /api/ai/chat

POST /api/ai/product-qa

POST /api/ai/generate-script

POST /api/ai/analyze-customer

POST /api/ai/training/start

POST /api/ai/training/message

POST /api/ai/compliance/check

GET /api/customers

GET /api/customers/:id

POST /api/customers/:id/followups

GET /api/knowledge

POST /api/knowledge/upload

POST /api/knowledge/:id/publish

GET /api/community

POST /api/community/posts

GET /api/admin/statistics
```

统一：

```json
{
  "success": true,
  "data": {},
  "message": "",
  "request_id": ""
}
```

错误：

```json
{
  "success": false,
  "error": {
    "code": "",
    "message": ""
  },
  "request_id": ""
}
```

---

# 三十三、前端工程要求

优先：

```text
React
TypeScript
Vite
Tailwind CSS
shadcn/ui 或等价高质量组件体系
React Query
React Router
Zustand 或等价状态方案
```

但：

> 如果仓库已有成熟技术栈，优先沿用现有技术栈。

不要为了炫技切换技术栈。

前端要求：

- TypeScript strict
- ESLint
- Prettier
- 组件化
- 可复用
- API 与 UI 分离
- Loading
- Error
- Empty
- Skeleton
- Toast
- Modal
- Pagination
- 搜索
- 筛选

每一个页面都要考虑：

```text
加载态
空态
错误态
成功态
权限不足态
```

---

# 三十四、后端工程要求

如果没有现有约束，推荐：

```text
Python
FastAPI
SQLAlchemy
Pydantic
PostgreSQL
Redis
Celery / Background Tasks
```

代码必须分层：

```text
routers
services
repositories
models
schemas
core
integrations
ai
rag
security
```

禁止把大量业务逻辑塞在 Router 中。

---

# 三十五、RAG 文档处理

如果实现 PDF / Word / PPT 文档解析：

支持：

```text
PDF
DOCX
PPTX
TXT
Markdown
```

处理流程：

```text
Upload
→ Parse
→ Normalize
→ Structure
→ Chunk
→ Metadata
→ Embed
→ Index
```

同时保留：

```text
document_id
page
section
source_text
```

保证引用可以回到原文。

---

# 三十六、前端 AI 体验

AI 产品必须做到：

### Streaming

优先支持 SSE。

例如：

```text
AI正在思考……
↓
逐字流式输出
↓
引用卡片
↓
风险提示
```

不要每次等待 10 秒以后突然一次性出现。

---

# 三十七、AI Loading 文案

不要写：

> Loading...

应该根据场景：

```text
正在检索安诊保产品资料…
正在分析客户画像…
正在生成个性化话术…
正在进行合规检查…
正在生成陪练评价…
```

增加产品感。

---

# 三十八、错误处理

例如模型失败：

不要：

```text
500 Internal Server Error
```

而是：

```text
AI 暂时无法响应

可能原因：
模型服务暂时不可用

你可以：
[再次尝试]
```

后台日志保留技术错误。

前台不暴露敏感 Stack Trace。

---

# 三十九、搜索体验

知识库、客户、社区、话术全部支持：

- 即时搜索
- 模糊搜索
- 标签过滤
- 时间过滤
- 分类过滤

---

# 四十、权限设计

至少做：

```text
代理人
├── 自己的客户
├── 自己的记录
├── 自己的训练
└── 公共知识

主管
├── 团队客户
├── 团队成员
├── 团队数据
└── 团队案例

管理员
└── 全局能力
```

权限不能只靠 URL 判断。

必须后端实际验证。

---

# 四十一、审计

至少记录：

```text
登录
退出
查看客户
查看敏感数据
AI问答
知识库访问
知识库发布
话术生成
合规审核
发送确认
管理员操作
```

---

# 四十二、日志体系

实现：

```text
app log
error log
security log
audit log
ai log
```

所有 AI 请求至少记录：

```text
request_id
user_id
model
temperature
tokens（若可获得）
latency
prompt_version
knowledge_sources
risk_level
result_status
```

不要记录不必要的明文敏感客户数据。

---

# 四十三、可观测性

至少做：

```text
请求耗时
AI耗时
数据库耗时
RAG检索耗时
模型调用失败率
API错误率
```

预留：

```text
OpenTelemetry
Prometheus
Grafana
```

---

# 四十四、测试要求

必须提供：

## 单元测试

测试：

- auth
- RBAC
- RAG
- compliance
- customer analysis
- script generation
- score calculation

## API 测试

覆盖：

```text
登录
权限
客户
知识库
AI
社区
后台
```

## 前端测试

至少覆盖：

```text
登录
首页
AI问答
客户详情
陪练
后台知识库
```

## E2E

至少完成：

```text
登录
→ 进入工作台
→ 查询产品
→ 查看依据
→ 选择客户
→ 生成话术
→ 合规检查
→ 开始陪练
→ 查看评分
```

---

# 四十五、开发顺序

不要一次性生成全部代码。

严格按照：

## Phase 1

基础工程：

- 项目初始化
- Docker
- 数据库
- Redis
- Auth
- RBAC
- 基础 UI

## Phase 2

工作台：

- Dashboard
- Navigation
- Notifications

## Phase 3

知识库 + RAG：

- Upload
- Parse
- Chunk
- Embedding
- Retrieval
- Rerank
- Citation

## Phase 4

AI 产品专家：

- Chat
- Streaming
- Citation
- Feedback

## Phase 5

客户 360：

- Customers
- Detail
- Tags
- Interaction
- AI analysis

## Phase 6

AI 话术：

- Generation
- Multi-style
- Compliance
- Copy

## Phase 7

AI 陪练：

- Scenario
- Roleplay
- Scoring
- History

## Phase 8

AI 社区：

- Posts
- Comments
- Likes
- AI summary
- Knowledge promotion

## Phase 9

管理后台：

- User
- Knowledge
- Scenarios
- Compliance
- Audit
- Analytics

## Phase 10

测试 + 性能 + 安全 + Docker + README

---

# 四十六、不要偷懒

以下行为禁止：

### 禁止 1

用静态 HTML 假装动态产品。

### 禁止 2

所有按钮点了没反应。

### 禁止 3

大量页面都写：

> Coming Soon

### 禁止 4

用前端硬编码业务数据。

### 禁止 5

在代码里硬编码 API Key。

### 禁止 6

把 AI 能力写成随机字符串生成。

### 禁止 7

只做 UI，不做后端。

### 禁止 8

为了完成任务删除原有功能。

### 禁止 9

为了省时间跳过权限。

### 禁止 10

用一个巨大的文件承载整个项目。

---

# 四十七、如果真实 AI API 暂时不可用

实现：

```text
MockProvider
```

但是接口必须与真实 AI Provider 完全一致。

比如：

```python
class AIProvider:
    async def chat(...)
    async def embed(...)
    async def rerank(...)
```

这样未来：

```text
Mock
↓
DeepSeek
↓
Qwen
↓
OpenAI-compatible
```

不需要改业务层。

---

# 四十八、如果 Dify 可接入

PPT 中提出过 Dify Workflow / Dataset 作为候选应用编排能力。

但不要把整个应用架构绑死在 Dify 上。

原则：

```text
核心业务逻辑
↓
自己的后端

AI编排
↓
可选择Dify

模型
↓
AI Gateway
```

必须保持可替换。

---

# 四十九、数据初始化

项目启动以后执行：

```bash
docker compose up -d
```

然后：

```bash
make init
```

自动：

```text
创建数据库
迁移
创建管理员
创建 Demo 用户
创建 Demo 产品
导入 Demo 知识
导入陪练
导入社区
```

最终做到：

> 克隆项目 → 配置 env → 一条命令启动。

---

# 五十、Docker

最终必须提供：

```text
docker-compose.yml
.env.example
Dockerfile
```

基础服务：

```text
frontend
backend
postgres
redis
vector-db
```

如果 Vector DB 使用 PostgreSQL pgvector，也可以不额外部署 Milvus。

架构优先简单可靠。

---

# 五十一、README

README 至少包括：

```text
项目介绍
功能介绍
架构图
技术栈
本地启动
环境变量
数据库迁移
Demo账号
AI配置
RAG配置
Docker
测试
部署
目录结构
常见问题
```

README必须让一个没有参与开发的人也能够成功运行项目。

---

# 五十二、开发过程中的行为要求

你作为 Codex Agent，不要每做一点事情就问我：

> “要不要继续？”

除非出现真正无法解决的业务冲突。

否则：

> 自主分析 → 自主实施 → 自主验证 → 修复问题 → 继续推进。

如果发现需求存在合理歧义：

优先选择：

> 更安全、更可扩展、更符合企业产品的方法。

同时把最终决定写入：

```text
docs/decisions.md
```

---

# 五十三、建立项目文档

必须生成：

```text
docs/
├── product-requirements.md
├── architecture.md
├── information-architecture.md
├── user-flows.md
├── database.md
├── api.md
├── rag.md
├── ai-agents.md
├── compliance.md
├── security.md
├── testing.md
├── deployment.md
└── decisions.md
```

代码之外，这些文档必须同步更新。

---

# 五十四、核心产品原则

整个系统必须始终遵守：

## 1. AI 是副驾，不是代理人

AI 提供：

> 信息、分析、建议、训练。

最终业务责任由人承担。

## 2. 产品知识必须可追溯

所有关键产品回答必须有出处。

## 3. 高风险场景必须人工确认

特别是：

> 核保、理赔、健康告知、客户最终承诺。

## 4. 客户事实与 AI 推断必须区分

不能把 AI 猜测当成真实事实。

## 5. 数据最小化

只收集必要信息。

## 6. 组织经验必须沉淀

优秀代理人的经验应该成为公司资产。

---

# 五十五、第一阶段 KPI 对应到产品

PPT设定：

```text
人均产能目标 +15%～25%
客户转化率 +3～5个百分点
陪练 ≥ 3场/人/月
AI问答满意度持续提升
```

这些指标必须在产品中预留数据结构，不要现在虚构结果。

第一版重点观察：

```text
DAU
AI问答次数
回答采纳率
话术生成次数
话术复制率
陪练人数
陪练完成次数
知识库命中率
AI错误率
合规拦截率
```

---

# 五十六、视觉产品细节要求

我要的是：

> 真正可以给企业内部员工长期使用的产品。

所以请重点注意：

### 排版

- 8px spacing system
- 清晰层级
- 统一圆角
- 统一卡片体系
- 合理留白

### 字体

中文优先使用系统字体。

### Icon

统一图标系统。

### 表单

统一：

```text
Label
Input
Help
Error
Success
```

### 表格

必须：

- 排序
- 筛选
- 分页
- Hover
- 状态
- 空数据
- 加载

### AI Chat

必须：

- Markdown
- Code-like knowledge citation block
- Source card
- Feedback
- Copy
- Retry

---

# 五十七、非常重要：不要把产品做得像 ChatGPT

这是企业 AI 产品。

视觉重点应该是：

> 工作流

而不是：

> 聊天。

AI 是贯穿产品的能力。

例如：

```text
客户页面
    ↓
[AI分析]

知识库
    ↓
[AI总结]

话术
    ↓
[AI生成]

陪练
    ↓
[AI训练]

社区
    ↓
[AI复盘]
```

所以整个产品的视觉语言应该是：

> AI-native Enterprise Software

而不是：

> ChatGPT clone。

---

# 五十八、最终产品应该形成这样的结构

```text
                 安诊保 AI 副驾
                        │
       ┌────────────────┼────────────────┐
       │                │                │
      工作台          客户工作台        AI中心
       │                │                │
       │                │        ┌───────┼───────┐
       │                │        │       │       │
       │                │       问答    话术    陪练
       │                │        │       │       │
       └────────────────┼────────┴───────┴───────┘
                        │
                    AI 销售 Agent
                        │
                 ┌──────┴──────┐
                 │             │
              知识库         合规中心
                 │             │
                 └──────┬──────┘
                        │
                   AI 数据飞轮
                        │
                  ┌─────┴─────┐
                  │           │
                AI社区      数据看板
```

---

# 五十九、成功标准

当你完成开发以后，必须达到：

### 产品层面

用户可以完整完成：

```text
登录
→ 查看工作台
→ 问产品问题
→ 阅读条款出处
→ 选择客户
→ 查看客户画像
→ 生成销售话术
→ 自动做合规检查
→ 进入AI陪练
→ 完成训练
→ 查看评分
→ 进入社区
```

### 技术层面

必须：

```text
前端运行
后端运行
数据库运行
API运行
AI Mock运行
RAG运行
权限运行
日志运行
Docker运行
测试通过
```

### 代码层面

必须：

```text
无明显 TODO
无明显死代码
无大规模硬编码
无明文 Secret
无明显 TypeScript error
无明显 Python lint error
```

---

# 六十、你的最终执行任务

现在开始执行。

不要只给我方案。

不要只给我架构图。

不要只给我 UI。

**直接开始构建整个项目。**

执行顺序：

```text
1. 检查当前仓库
2. 分析已有代码
3. 确定技术栈
4. 生成 docs
5. 建立数据库
6. 建立后端
7. 建立前端
8. 建立 AI Gateway
9. 建立 RAG
10. 建立 AI 产品专家
11. 建立客户360
12. 建立 AI话术
13. 建立 AI陪练
14. 建立 AI社区
15. 建立管理后台
16. 建立合规中心
17. 建立审计
18. Seed Demo 数据
19. 编写测试
20. Docker 化
21. 本地运行
22. 完整联调
23. 修复错误
24. 最终检查
```

---

# 六十一、最终交付格式

完成以后向我汇报：

## 1. 项目完成度

```text
核心功能完成率
```

## 2. 当前技术栈

## 3. 项目目录

## 4. 已实现功能

## 5. Demo账号

## 6. 启动方式

## 7. API地址

## 8. 前端地址

## 9. 数据库结构

## 10. AI配置方法

## 11. RAG使用方法

## 12. 测试结果

## 13. 已知问题

## 14. 下一阶段建议

---

# 六十二、最重要的最终要求

请记住：

**不要把它做成一个“看起来很厉害的 AI Demo”。**

我要的是：

> **一个真正具备企业产品雏形、能够进行内部试点、后续可以不断扩展成为“代理人 AI OS”的产品。**

最终产品要体现：

```text
企业级
+
AI Native
+
销售工作流
+
RAG
+
Agent
+
合规
+
权限
+
数据闭环
+
可扩展
```

现在开始执行。

先检查仓库，再开始实施。

不要等待我确认下一步。