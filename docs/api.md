# API 接口设计文档 — 安诊保 AI 副驾

> **文档状态**：当前有效 · 端点清单已与 `backend/app/api/v1/` 实际代码对齐（**92 端点**，源码统计）；下方详细设计为参考规范
> 最后校准：2026-08-17

---

### 已验证端点清单（源码统计，2026-08-20，共 92 个）

| 模块 | 方法 | 路径 |
|------|------|------|
| admin | GET | `/api/v1/users` |
| admin | POST | `/api/v1/users` |
| admin | PUT | `/api/v1/users/{user_id}` |
| admin | POST | `/api/v1/users/{user_id}/disable` |
| admin | POST | `/api/v1/users/{user_id}/enable` |
| admin | GET | `/api/v1/audit-logs` |
| admin | GET | `/api/v1/analytics/overview` |
| admin | GET | `/api/v1/analytics/ai-usage` |
| admin | GET | `/api/v1/analytics/training` |
| admin | GET | `/api/v1/analytics/community` |
| admin | GET | `/api/v1/compliance/rules` |
| admin | POST | `/api/v1/compliance/rules` |
| admin | PUT | `/api/v1/compliance/rules/{rule_id}` |
| admin | GET | `/api/v1/compliance/reviews` |
| admin | POST | `/api/v1/compliance/reviews/{review_id}/process` |
| admin | GET | `/api/v1/community/posts` |
| admin | POST | `/api/v1/community/posts/{post_id}/pin` |
| admin | POST | `/api/v1/community/posts/{post_id}/recommend` |
| admin | DELETE | `/api/v1/community/posts/{post_id}` |
| admin | GET | `/api/v1/scripts` |
| admin | POST | `/api/v1/scripts/{script_id}/approve` |
| admin | GET | `/api/v1/training/scenarios` |
| admin | POST | `/api/v1/training/scenarios` |
| admin | PUT | `/api/v1/training/scenarios/{scenario_id}` |
| admin | POST | `/api/v1/training/scenarios/{scenario_id}/publish` |
| admin | DELETE | `/api/v1/training/scenarios/{scenario_id}` |
| admin | GET | `/api/v1/settings` |
| admin | PUT | `/api/v1/settings` |
| ai | POST | `/api/v1/product-qa/chat` |
| ai | GET | `/api/v1/product-qa/conversations` |
| ai | GET | `/api/v1/product-qa/conversations/{conversation_id}` |
| auth | POST | `/api/v1/login` |
| auth | POST | `/api/v1/refresh` |
| auth | POST | `/api/v1/logout` |
| auth | GET | `/api/v1/me` |
| community | GET | `/api/v1/posts` |
| community | GET | `/api/v1/favorites` |
| community | GET | `/api/v1/posts/{post_id}` |
| community | POST | `/api/v1/posts` |
| community | PUT | `/api/v1/posts/{post_id}` |
| community | DELETE | `/api/v1/posts/{post_id}` |
| community | POST | `/api/v1/posts/{post_id}/like` |
| community | POST | `/api/v1/posts/{post_id}/favorite` |
| community | GET | `/api/v1/posts/{post_id}/comments` |
| community | POST | `/api/v1/posts/{post_id}/comments` |
| community | GET | `/api/v1/posts/{post_id}/ai-summary` |
| customer | GET | `/api/v1` |
| customer | GET | `/api/v1/{customer_id}` |
| customer | POST | `/api/v1` |
| customer | PUT | `/api/v1/{customer_id}` |
| customer | DELETE | `/api/v1/{customer_id}` |
| customer | POST | `/api/v1/{customer_id}/interactions` |
| customer | POST | `/api/v1/{customer_id}/followups` |
| customer | POST | `/api/v1/{customer_id}/ai-analysis` |
| dashboard | GET | `/api/v1` |
| growth | GET | `/api/v1/overview` |
| growth | GET | `/api/v1/courses/{course_id}` |
| growth | GET | `/api/v1/leaderboard` |
| growth | GET | `/api/v1/achievements` |
| health | GET | `/api/v1/health` |
| health | GET | `/api/v1/ready` |
| health | GET | `/api/v1/health/detail` |
| knowledge | GET | `/api/v1/knowledge-bases` |
| knowledge | POST | `/api/v1/knowledge-bases` |
| knowledge | GET | `/api/v1/knowledge-bases/{kb_id}` |
| knowledge | PUT | `/api/v1/knowledge-bases/{kb_id}` |
| knowledge | DELETE | `/api/v1/knowledge-bases/{kb_id}` |
| knowledge | GET | `/api/v1/knowledge-bases/{kb_id}/documents` |
| knowledge | POST | `/api/v1/knowledge-bases/{kb_id}/documents/upload` |
| knowledge | POST | `/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/publish` |
| knowledge | DELETE | `/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}` |
| notification | GET | `/api/v1` |
| notification | POST | `/api/v1/read` |
| notification | GET | `/api/v1/preferences` |
| notification | PUT | `/api/v1/preferences` |
| script | POST | `/api/v1/generate` |
| script | POST | `/api/v1/check-compliance` |
| script | GET | `/api/v1` |
| script | GET | `/api/v1/{script_id}` |
| script | POST | `/api/v1/{script_id}/favorite` |
| script | DELETE | `/api/v1/{script_id}` |
| training | GET | `/api/v1/scenarios` |
| training | GET | `/api/v1/scenarios/{scenario_id}` |
| training | POST | `/api/v1/sessions` |
| training | GET | `/api/v1/sessions` |
| training | GET | `/api/v1/sessions/{session_id}` |
| training | POST | `/api/v1/sessions/{session_id}/messages` |
| training | POST | `/api/v1/sessions/{session_id}/complete` |
| training | GET | `/api/v1/stats` |

---


> **版本**: v1.0.0-draft
> **最后更新**: 2025-01
> **技术栈**: Python FastAPI + SSE
> **通信协议**: HTTPS (REST + Server-Sent Events)

---

## 目录

1. [API 设计规范](#1-api-设计规范)
2. [错误码定义](#2-错误码定义)
3. [认证与用户 API](#3-认证与用户-api)
4. [工作台 API](#4-工作台-api)
5. [AI 产品专家 API](#5-ai-产品专家-api)
6. [客户 360 API](#6-客户-360-api)
7. [AI 话术 API](#7-ai-话术-api)
8. [AI 陪练 API](#8-ai-陪练-api)
9. [AI 社区 API](#9-ai-社区-api)
10. [我的成长 API](#10-我的成长-api)
11. [消息中心 API](#11-消息中心-api)
12. [管理后台 API](#12-管理后台-api)
13. [SSE 流式响应规范](#13-sse-流式响应规范)

---

## 1. API 设计规范

### 1.1 RESTful 风格

| 约束 | 说明 |
|------|------|
| 资源命名 | 使用 **名词复数**，如 `/customers`、`/conversations` |
| HTTP 动词 | `GET`(查询)、`POST`(创建)、`PUT`(全量更新)、`PATCH`(部分更新)、`DELETE`(删除) |
| URL 层级 | 资源嵌套不超过 **两层**，如 `/customers/:id/interactions` |
| 动作接口 | 非CRUD操作使用 **动词后缀**，如 `/ai/scripts/generate`、`/customers/:id/ai-analysis` |
| 小写+连字符 | URL 路径使用小写字母，单词间以连字符 `-` 连接 |

### 1.2 统一响应格式

**成功响应**:

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "request_id": "req_7f3a1b2c4d5e"
}
```

**错误响应**:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_001",
    "message": "参数校验失败：phone 字段格式不正确"
  },
  "request_id": "req_7f3a1b2c4d5e"
}
```

**分页响应**:

```json
{
  "success": true,
  "data": {
    "items": [],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  },
  "message": "",
  "request_id": "req_xxx"
}
```

### 1.3 版本管理

- 所有接口统一前缀：**`/api/v1/`**
- 版本号采用 **主版本号** 管理，不使用次版本号
- 新版本发布时旧版本至少保留 **3 个月兼容期**
- 版本弃用通过响应头 `X-API-Deprecated: true` + `Sunset: <日期>` 通知

### 1.4 认证方式

采用 **JWT Bearer Token** 方式：

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

| 项目 | 说明 |
|------|------|
| Token 类型 | Access Token (短期) + Refresh Token (长期) |
| Access Token 有效期 | **2 小时** |
| Refresh Token 有效期 | **7 天** |
| Token 存储 | 客户端 localStorage 或 HttpOnly Cookie |
| 多设备策略 | 同一账号最多同时 **3 个设备** 登录 |
| RBAC 角色 | `agent`(代理人)、`supervisor`(主管)、`admin`(管理员) |

### 1.5 错误码体系

- 采用 **模块前缀_序号** 格式：`AUTH_001`、`VALIDATION_001`
- HTTP 状态码与业务错误码对应
- 每个错误码附中文描述信息，便于前端展示

### 1.6 通用查询参数

**分页参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码，从 1 开始 |
| `page_size` | int | 20 | 每页条数，最大 100 |

**排序参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sort_by` | string | `created_at` | 排序字段 |
| `sort_order` | string | `desc` | 排序方向：`asc` / `desc` |

**搜索参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `keyword` | string | 全文搜索关键词 |
| `filters` | object | 结构化筛选条件（JSON） |

### 1.7 Rate Limit

| 接口类型 | 限制 | 说明 |
|----------|------|------|
| 普通查询接口 | 60 次/分钟 | 基于 API Key 或用户 ID |
| AI 接口 (SSE) | 20 次/分钟 | 消耗 AI 算力 |
| 认证接口 | 10 次/分钟 | 防暴力破解 |
| 文件上传 | 5 次/分钟 | 防滥用 |

- 响应头携带限流信息：

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706140800
```

- 超限返回 HTTP `429` + `RATE_LIMIT_001` 错误码

---

## 2. 错误码定义

### 2.1 错误码总表

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| `AUTH_001` | 401 | 未认证 — 缺少 Token 或 Token 格式错误 |
| `AUTH_002` | 403 | 权限不足 — 当前角色无权访问该资源 |
| `AUTH_003` | 401 | Token 过期 — Access Token 已失效，请使用 Refresh Token |
| `AUTH_004` | 401 | Refresh Token 无效或已过期 |
| `AUTH_005` | 403 | 账号已被禁用 |
| `VALIDATION_001` | 422 | 参数校验失败 — 请求体或查询参数不合法 |
| `VALIDATION_002` | 422 | 文件格式不支持 |
| `VALIDATION_003` | 413 | 文件大小超限 |
| `NOT_FOUND_001` | 404 | 资源不存在 — 请求的资源 ID 无效或已删除 |
| `AI_001` | 503 | AI 服务不可用 — 大模型服务异常 |
| `AI_002` | 503 | AI 请求超时 — 响应时间超过阈值 |
| `AI_003` | 503 | AI 生成内容异常 — 输出不合规或格式错误 |
| `RAG_001` | 404 | 知识库未找到相关内容 — 检索结果为空 |
| `RAG_002` | 500 | 知识库索引异常 — Embedding 或检索出错 |
| `COMPLIANCE_001` | 200 | 合规检查不通过 — 话术内容触犯合规规则 |
| `COMPLIANCE_002` | 422 | 合规规则不完整 — 缺少必要字段 |
| `RATE_LIMIT_001` | 429 | 请求频率超限 |
| `INTERNAL_001` | 500 | 服务器内部错误 |
| `INTERNAL_002` | 503 | 数据库连接异常 |
| `INTERNAL_003` | 503 | 缓存服务异常 |
| `BUSINESS_001` | 409 | 业务冲突 — 如重复创建、状态不允许该操作 |
| `FILE_001` | 400 | 文件上传失败 |

### 2.2 校验失败详情格式

当错误码为 `VALIDATION_001` 时，`error` 对象额外包含 `details` 字段：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_001",
    "message": "参数校验失败",
    "details": [
      {
        "field": "phone",
        "message": "手机号格式不正确",
        "value": "123"
      },
      {
        "field": "customer_name",
        "message": "此字段为必填项"
      }
    ]
  },
  "request_id": "req_xxx"
}
```

---

## 3. 认证与用户 API

### 3.1 用户登录

```
POST /api/v1/auth/login
```

**请求体**:

```json
{
  "phone": "13800138000",
  "verification_code": "123456"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phone` | string | ✅ | 手机号，11 位 |
| `verification_code` | string | ✅ | 短信验证码，6 位数字 |

> **[Mock] Demo 模式**：手机号 `13800138000`，验证码 `123456`，绕过短信网关直接登录。

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "user": {
      "id": "usr_a1b2c3d4",
      "name": "张明",
      "phone": "138****8000",
      "avatar": "https://cdn.example.com/avatars/default.png",
      "role": "agent",
      "role_label": "保险代理人",
      "organization": {
        "id": "org_001",
        "name": "华东区第一营业部"
      },
      "permissions": ["product:read", "customer:read", "customer:write", "ai:use"],
      "last_login_at": "2025-01-15T08:30:00+08:00"
    }
  },
  "message": "登录成功",
  "request_id": "req_xxx"
}
```

**错误响应**:

| 错误码 | 说明 |
|--------|------|
| `VALIDATION_001` | 手机号格式错误 |
| `AUTH_001` | 验证码错误或已过期 |
| `AUTH_005` | 账号已被禁用 |

---

### 3.2 刷新 Token

```
POST /api/v1/auth/refresh
```

**请求体**:

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 7200
  },
  "message": "",
  "request_id": "req_xxx"
}
```

**错误响应**:

| 错误码 | 说明 |
|--------|------|
| `AUTH_004` | Refresh Token 无效或已过期 |

---

### 3.3 退出登录

```
POST /api/v1/auth/logout
```

**请求头**:

```
Authorization: Bearer <access_token>
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": null,
  "message": "退出成功",
  "request_id": "req_xxx"
}
```

> 后端将 Token 加入黑名单，失效即刻生效。

---

### 3.4 获取当前用户信息

```
GET /api/v1/auth/me
```

**请求头**:

```
Authorization: Bearer <access_token>
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "usr_a1b2c3d4",
    "name": "张明",
    "phone": "138****8000",
    "avatar": "https://cdn.example.com/avatars/default.png",
    "role": "agent",
    "role_label": "保险代理人",
    "organization": {
      "id": "org_001",
      "name": "华东区第一营业部"
    },
    "permissions": ["product:read", "customer:read", "customer:write", "ai:use"],
    "created_at": "2024-06-01T10:00:00+08:00",
    "last_login_at": "2025-01-15T08:30:00+08:00"
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

## 4. 工作台 API

> **权限**: 登录用户（JWT Bearer）。数据按当前用户隔离（负责的客户 + 自身活动）。

### 4.1 工作台概览

```
GET /api/v1/dashboard
```

**说明**: 生产模式从数据库真实聚合：今日统计（今日互动/成交保单/待跟进客户/AI 问答次数）、AI 建议（由待跟进/高意向/未读通知/最近陪练推导）、最近活动（互动/陪练/话术/问答合并）、未读通知数。

**成功响应** `200`:

```json
{
  "greeting": "上午好",
  "user_name": "林思远",
  "today_stats": [
    {"label": "今日互动", "value": "5", "sub": "+2 较昨日", "trend": "up"},
    {"label": "成交保单", "value": "1", "sub": "2个高意向", "trend": "neutral"},
    {"label": "待跟进客户", "value": "3", "sub": "待处理跟进", "trend": "neutral"},
    {"label": "AI 问答次数", "value": "8", "sub": "今日累计", "trend": "neutral"}
  ],
  "ai_suggestions": [
    {
      "id": "...",
      "title": "有客户待跟进",
      "description": "您有 3 个待跟进客户，建议尽快安排回访。",
      "tag": "紧急跟进",
      "tag_variant": "error",
      "action_url": "/customers",
      "created_at": "2026-08-15T01:00:00+00:00"
    }
  ],
  "quick_actions": [
    {"label": "新建客户", "icon": "👤", "path": "/customers/new", "color": "bg-primary/10 text-primary"}
  ],
  "recent_activities": [
    {"id": "...", "type": "followup", "title": "互动：王女士", "description": "通话记录", "time": "5分钟前", "icon": "📞"}
  ],
  "unread_notifications": 2
}
```

## 5. AI 产品专家 API

> **权限**: `agent`、`supervisor`

### 5.1 产品问答对话（SSE）

```
POST /api/v1/ai/product-qa/chat
```

**Content-Type**: `application/json`
**Accept**: `text/event-stream`

**请求体**:

```json
{
  "question": "百万医疗险和重疾险的区别是什么？",
  "product_id": "prod_001",
  "knowledge_scope": "medical_insurance",
  "conversation_id": "conv_a1b2c3"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | ✅ | 用户问题，最大 500 字 |
| `product_id` | string | ❌ | 关联产品 ID，限定知识检索范围 |
| `knowledge_scope` | string | ❌ | 知识范围：`all`、`medical_insurance`、`life_insurance`、`critical_illness`、`annuity` |
| `conversation_id` | string | ❌ | 续接已有对话，不传则创建新对话 |

**SSE 响应流**:

```
event: message_start
data: {"conversation_id": "conv_a1b2c3", "message_id": "msg_x1y2z3"}

event: token
data: {"content": "百万"}

event: token
data: {"content": "医疗险"}

event: token
data: {"content": "和"}

event: token
data: {"content": "重疾险"}

event: token
data: {"content": "是两种"}

event: related_products
data: {"products": [{"id": "prod_001", "name": "安诊保百万医疗2025", "category": "medical_insurance"}, {"id": "prod_002", "name": "守护终身重疾险", "category": "critical_illness"}]}

event: reference_sources
data: {"sources": [{"document_id": "doc_001", "title": "百万医疗险产品条款 v3.2", "relevance": 0.95, "chunk_text": "..."}, {"document_id": "doc_005", "title": "重疾险对比分析", "relevance": 0.88, "chunk_text": "..."}]}

event: message_complete
data: {"message_id": "msg_x1y2z3", "token_count": 256, "sources_count": 2}
```

> 详见 [第 13 节 SSE 流式响应规范](#13-sse-流式响应规范)。

---

### 5.2 对话列表

```
GET /api/v1/ai/product-qa/conversations
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | string | — | 搜索对话标题或内容 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |
| `sort_by` | string | `updated_at` | 排序字段 |
| `sort_order` | string | `desc` | 排序方向 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "conv_a1b2c3",
        "title": "百万医疗险与重疾险对比",
        "last_message_preview": "两种保险的保障范围和理赔方式有本质区别...",
        "message_count": 8,
        "product_ids": ["prod_001", "prod_002"],
        "created_at": "2025-01-15T10:00:00+08:00",
        "updated_at": "2025-01-15T14:30:00+08:00"
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 5.3 对话详情

```
GET /api/v1/ai/product-qa/conversations/:id
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "conv_a1b2c3",
    "title": "百万医疗险与重疾险对比",
    "messages": [
      {
        "id": "msg_001",
        "role": "user",
        "content": "百万医疗险和重疾险的区别是什么？",
        "created_at": "2025-01-15T10:00:00+08:00"
      },
      {
        "id": "msg_002",
        "role": "assistant",
        "content": "百万医疗险和重疾险是两种不同类型的健康保险...",
        "sources": [
          {
            "document_id": "doc_001",
            "title": "百万医疗险产品条款 v3.2",
            "relevance": 0.95
          }
        ],
        "related_products": [
          {"id": "prod_001", "name": "安诊保百万医疗2025"}
        ],
        "feedback": null,
        "created_at": "2025-01-15T10:00:05+08:00"
      }
    ],
    "product_ids": ["prod_001", "prod_002"],
    "created_at": "2025-01-15T10:00:00+08:00",
    "updated_at": "2025-01-15T14:30:00+08:00"
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 5.4 消息反馈

```
POST /api/v1/ai/product-qa/feedback
```

**请求体**:

```json
{
  "message_id": "msg_x1y2z3",
  "type": "dislike",
  "reason": "回答中关于免赔额的描述与产品条款不符"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message_id` | string | ✅ | 消息 ID |
| `type` | string | ✅ | 反馈类型：`like`、`dislike`、`error` |
| `reason` | string | ❌ | 反馈原因，`dislike` 和 `error` 时建议填写 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": null,
  "message": "感谢反馈",
  "request_id": "req_xxx"
}
```

---

## 6. 客户 360 API

> **权限**: `agent`（仅自己的客户）、`supervisor`（团队客户）、`admin`（全部客户）

### 6.1 客户列表

```
GET /api/v1/customers
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | string | — | 搜索客户姓名、手机号、备注 |
| `tags` | string[] | — | 标签筛选，多选 |
| `stage` | string | — | 客户阶段：`new_lead`、`initial_contact`、`needs_analysis`、`proposal`、`negotiation`、`closed_won`、`closed_lost`、`inactive` |
| `intent_min` | int | — | 购买意向最低分（0-100） |
| `intent_max` | int | — | 购买意向最高分（0-100） |
| `source` | string | — | 客户来源：`referral`、`online`、`offline`、`cold_call` |
| `sort_by` | string | `updated_at` | 排序字段：`created_at`、`updated_at`、`intent_score`、`name` |
| `sort_order` | string | `desc` | 排序方向 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数，最大 100 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "cus_001",
        "name": "李伟",
        "phone": "139****5678",
        "age": 35,
        "gender": "male",
        "avatar": null,
        "tags": ["高净值", "健康险意向"],
        "stage": "needs_analysis",
        "stage_label": "需求分析",
        "intent_score": 72,
        "last_interaction_at": "2025-01-14T16:00:00+08:00",
        "next_follow_up_at": "2025-01-16T10:00:00+08:00",
        "assigned_agent": {
          "id": "usr_a1b2c3d4",
          "name": "张明"
        },
        "created_at": "2025-01-05T10:00:00+08:00",
        "updated_at": "2025-01-14T16:00:00+08:00"
      }
    ],
    "total": 128,
    "page": 1,
    "page_size": 20,
    "total_pages": 7
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 6.2 客户详情

```
GET /api/v1/customers/:id
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "cus_001",
    "name": "李伟",
    "phone": "13912345678",
    "age": 35,
    "gender": "male",
    "birthday": "1990-05-20",
    "id_number_last4": "5678",
    "email": "liwei@example.com",
    "occupation": "互联网公司产品经理",
    "address": "上海市浦东新区",
    "tags": ["高净值", "健康险意向", "有孩家庭"],
    "stage": "needs_analysis",
    "stage_label": "需求分析",
    "intent_score": 72,
    "intent_trend": "+5",
    "source": "referral",
    "source_label": "转介绍",
    "notes": "客户对保险有一定认知，比较理性，关注产品细节和条款。",
    "ai_analysis": {
      "risk_profile": "中等",
      "recommended_products": ["prod_001", "prod_005"],
      "key_concerns": ["保费预算", "理赔流程", "保障范围"],
      "communication_preference": "理性分析型",
      "family_situation": "已婚，有一子（3岁），妻子为教师",
      "last_analyzed_at": "2025-01-14T16:00:00+08:00"
    },
    "assigned_agent": {
      "id": "usr_a1b2c3d4",
      "name": "张明"
    },
    "created_at": "2025-01-05T10:00:00+08:00",
    "updated_at": "2025-01-14T16:00:00+08:00"
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 6.3 创建客户

```
POST /api/v1/customers
```

**请求体**:

```json
{
  "name": "王芳",
  "phone": "13812345678",
  "age": 30,
  "gender": "female",
  "birthday": "1995-03-15",
  "email": "wangfang@example.com",
  "occupation": "外企市场经理",
  "address": "上海市徐汇区",
  "source": "online",
  "tags": ["健康险意向"],
  "notes": "通过线上活动获取的意向客户"
}
```

**成功响应** `201`:

```json
{
  "success": true,
  "data": {
    "id": "cus_new_001",
    "name": "王芳",
    "stage": "new_lead",
    "intent_score": 50,
    "created_at": "2025-01-15T15:00:00+08:00"
  },
  "message": "客户创建成功",
  "request_id": "req_xxx"
}
```

---

### 6.4 更新客户

```
PUT /api/v1/customers/:id
```

**请求体**:

```json
{
  "name": "王芳",
  "phone": "13812345678",
  "age": 30,
  "gender": "female",
  "birthday": "1995-03-15",
  "email": "wangfang@example.com",
  "occupation": "外企市场经理",
  "address": "上海市徐汇区",
  "stage": "initial_contact",
  "notes": "已通过电话初步沟通，对重疾险有兴趣"
}
```

> 只需传入需要更新的字段，未传字段保持不变。

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "cus_new_001",
    "updated_fields": ["stage", "notes"],
    "updated_at": "2025-01-15T16:00:00+08:00"
  },
  "message": "客户信息已更新",
  "request_id": "req_xxx"
}
```

---

### 6.5 AI 客户分析（SSE）

```
POST /api/v1/customers/:id/ai-analysis
```

**Content-Type**: `application/json`
**Accept**: `text/event-stream`

**请求体**（可选）:

```json
{
  "analysis_type": "comprehensive",
  "include_product_recommendation": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `analysis_type` | string | ❌ | 分析类型：`comprehensive`(全面)、`quick`(快速)、`product_match`(产品匹配) |
| `include_product_recommendation` | bool | ❌ | 是否包含产品推荐，默认 `true` |

**SSE 响应流**:

```
event: analysis_start
data: {"customer_id": "cus_001", "analysis_id": "ana_001"}

event: step
data: {"step": "profile_analysis", "label": "客户画像分析", "progress": 20}

event: step
data: {"step": "risk_assessment", "label": "风险评估", "progress": 40}

event: step
data: {"step": "product_matching", "label": "产品智能匹配", "progress": 60}

event: step
data: {"step": "strategy_generation", "label": "沟通策略生成", "progress": 80}

event: result_risk_profile
data: {"risk_profile": "中等", "risk_factors": ["年龄因素", "家庭责任"], "risk_details": "..."}

event: result_recommendations
data: {"products": [{"id": "prod_001", "name": "安诊保百万医疗2025", "match_score": 92, "reason": "..."}], "communication_strategy": "..."}

event: analysis_complete
data: {"analysis_id": "ana_001", "token_count": 512, "duration_ms": 3200}
```

---

### 6.6 客户互动记录列表

```
GET /api/v1/customers/:id/interactions
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | — | 互动类型：`phone`、`wechat`、`offline`、`other` |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |
| `sort_by` | string | `created_at` | 排序字段 |
| `sort_order` | string | `desc` | 排序方向 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "inter_001",
        "type": "phone",
        "type_label": "电话沟通",
        "summary": "客户询问了百万医疗险的保障范围和保费，表示需要考虑几天。",
        "duration_minutes": 15,
        "outcome": "positive",
        "outcome_label": "有积极反馈",
        "recorded_by": {
          "id": "usr_a1b2c3d4",
          "name": "张明"
        },
        "attachments": [],
        "created_at": "2025-01-14T16:00:00+08:00"
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 6.7 新增互动记录

```
POST /api/v1/customers/:id/interactions
```

**请求体**:

```json
{
  "type": "wechat",
  "summary": "通过微信发送了产品对比表，客户对两款产品都有兴趣，约周六面谈。",
  "duration_minutes": 5,
  "outcome": "positive",
  "follow_up_needed": true,
  "follow_up_note": "周六下午2点在星巴克面谈，带上产品方案"
}
```

**成功响应** `201`:

```json
{
  "success": true,
  "data": {
    "id": "inter_002",
    "created_at": "2025-01-15T14:00:00+08:00"
  },
  "message": "互动记录已添加",
  "request_id": "req_xxx"
}
```

---

### 6.8 客户跟进计划列表

```
GET /api/v1/customers/:id/followups
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | string | — | 状态：`pending`、`completed`、`overdue`、`cancelled` |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "fup_001",
        "type": "phone_call",
        "type_label": "电话回访",
        "content": "回访百万医疗险咨询，解答客户关于续保条款的疑问",
        "scheduled_at": "2025-01-16T10:00:00+08:00",
        "status": "pending",
        "priority": "high",
        "related_interaction_id": "inter_001",
        "ai_suggestion": "建议先确认客户上次提到的预算顾虑是否已解决",
        "created_at": "2025-01-14T16:00:00+08:00"
      }
    ],
    "total": 3,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 6.9 创建跟进计划

```
POST /api/v1/customers/:id/followups
```

**请求体**:

```json
{
  "type": "offline_meeting",
  "content": "星巴克面谈，带上重疾险和医疗险对比方案",
  "scheduled_at": "2025-01-18T14:00:00+08:00",
  "priority": "medium"
}
```

**成功响应** `201`:

```json
{
  "success": true,
  "data": {
    "id": "fup_002",
    "status": "pending",
    "created_at": "2025-01-15T14:30:00+08:00"
  },
  "message": "跟进计划已创建",
  "request_id": "req_xxx"
}
```

---

### 6.10 更新客户标签

```
PUT /api/v1/customers/:id/tags
```

**请求体**:

```json
{
  "tags": ["高净值", "健康险意向", "有孩家庭", "重疾险关注"]
}
```

> **全量替换**：传入完整的标签列表，服务端将覆盖现有标签。

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "tags": ["高净值", "健康险意向", "有孩家庭", "重疾险关注"],
    "updated_at": "2025-01-15T15:00:00+08:00"
  },
  "message": "标签已更新",
  "request_id": "req_xxx"
}
```

---

## 7. AI 话术 API

> **权限**: `agent`、`supervisor`

### 7.1 生成话术（SSE）

```
POST /api/v1/scripts/generate
```

**Content-Type**: `application/json`
**Accept**: `text/event-stream`

**请求体**:

```json
{
  "customer_context": {
    "name": "张先生",
    "age": 35,
    "stage": "needs_analysis",
    "objection": "觉得保费太贵",
    "product_type": "医疗险",
    "insurance_knowledge": "初级"
  },
  "style": "professional",
  "product_type": "医疗险"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `customer_context` | object | ✅ | 客户上下文：name/age/customer_type/stage/objection/product_type/insurance_knowledge |
| `style` | string | ❌ | 指定风格（`affinity`/`professional`/`data_driven`/`concise`），不指定则生成全部 4 种 |
| `product_type` | string | ❌ | 产品类型；不传则回退到 customer_context.product_type |

**生成链路（Production 模式）**: 客户上下文 + 产品 → RAG 检索产品知识 → Confidence Gate → AI Gateway 流式生成 → 合规检查 → 持久化。

**SSE 响应流**:

```
event: generation_start
data: {"request_id": "...", "styles": ["professional"], "styles_display": ["专业型"]}

event: rag_context
data: {
  "product_type": "医疗险",
  "status": "ALLOW",           // ALLOW / REVIEW / REFUSE / ERROR
  "confidence": "HIGH",        // HIGH / MEDIUM / LOW / NONE
  "top_score": 0.85,
  "context_length": 320,
  "sources_count": 3,
  "citations": [
    {"document_id": "...", "document_title": "百万医疗险产品手册", "section": "保障范围", "source": "保障额度最高 600 万...", "score": 0.85}
  ]
}

event: style_start
data: {"style": "professional", "style_name": "专业型"}

event: token
data: {"style": "professional", "content": "张先生，关于您关注的医疗险..."}

event: style_complete
data: {
  "style": "professional",
  "style_name": "专业型",
  "content": "张先生，...",
  "compliance": {"status": "GREEN", "score": 100, "issues": []},
  "rag_status": "ALLOW",
  "citations": [...],
  "word_count": 412
}

event: generation_complete
data: {"request_id": "...", "total_styles": 1, "refused_styles": 0}
```

**RAG 拒答（Confidence Gate）**:

- `REFUSE`（RAG 未命中 / 低置信度）：不生成涉及产品事实的话术，逐风格发送 `style_refused` 事件，提示"知识库未找到充分产品依据"，不持久化伪造话术。
- `REVIEW`（中等置信度）：正常生成，但 `rag_status=REVIEW`，前端应提示人工确认。
- `ERROR`（知识库检索异常）：本次生成不带产品知识依据，前端应提示。
- AI 服务失败：逐风格发送 `style_error` 事件，返回可重试错误，不伪造话术。

**权限**: 生成的话术归属当前登录用户（`created_by`），仅本人可见/管理。

### 7.2 重新生成话术

```
POST /api/v1/ai/scripts/:id/regenerate
```

**请求体**:

```json
{
  "style": "professional",
  "adjustment_hint": "请更强调住院医疗的保障额度"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `style` | string | ❌ | 指定重新生成的风格，不传则全部重新生成 |
| `adjustment_hint` | string | ❌ | 调整提示词，引导 AI 调整生成方向 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "scr_001",
    "regenerated_styles": ["professional"],
    "updated_at": "2025-01-15T16:00:00+08:00"
  },
  "message": "话术已重新生成",
  "request_id": "req_xxx"
}
```

---

### 7.3 编辑话术

```
PUT /api/v1/ai/scripts/:id
```

**请求体**:

```json
{
  "style": "professional",
  "content": "修改后的话术内容..."
}
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "scr_001",
    "is_edited": true,
    "edited_by": {
      "id": "usr_a1b2c3d4",
      "name": "张明"
    },
    "edited_at": "2025-01-15T16:30:00+08:00"
  },
  "message": "话术已保存",
  "request_id": "req_xxx"
}
```

---

### 7.4 合规检查

```
POST /api/v1/ai/scripts/:id/compliance-check
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "script_id": "scr_001",
    "overall_result": "warning",
    "checks": [
      {
        "rule_id": "rule_003",
        "rule_name": "收益承诺禁止",
        "status": "passed",
        "detail": "未发现收益承诺类表述"
      },
      {
        "rule_id": "rule_007",
        "rule_name": "医疗术语规范",
        "status": "warning",
        "detail": "话术中「保证续保」表述需要修正为「保证续保至XX岁」",
        "position": "第3段第2行"
      },
      {
        "rule_id": "rule_012",
        "rule_name": "竞品贬低禁止",
        "status": "passed",
        "detail": "未发现不当竞品比较"
      }
    ],
    "passed_count": 2,
    "warning_count": 1,
    "violation_count": 0,
    "checked_at": "2025-01-15T16:30:00+08:00"
  },
  "message": "",
  "request_id": "req_xxx"
}
```

> 即使存在 `violation`，HTTP 状态码仍为 `200`，由前端根据 `overall_result` 展示提示。当存在 `violation` 时，错误码为 `COMPLIANCE_001`。

---

### 7.5 话术列表

```
GET /api/v1/ai/scripts
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | string | — | 搜索话术内容 |
| `objection_type` | string | — | 异议类型筛选 |
| `sales_stage` | string | — | 销售阶段筛选 |
| `customer_id` | string | — | 关联客户 ID |
| `is_favorite` | bool | — | 是否收藏 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "scr_001",
        "title": "保费异议-百万医疗险",
        "objection_type": "price",
        "sales_stage": "objection",
        "styles_count": 4,
        "compliance_status": "passed",
        "customer": {
          "id": "cus_001",
          "name": "李伟"
        },
        "is_favorite": false,
        "created_at": "2025-01-15T15:00:00+08:00"
      }
    ],
    "total": 35,
    "page": 1,
    "page_size": 20,
    "total_pages": 2
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 7.6 话术详情

```
GET /api/v1/ai/scripts/:id
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "scr_001",
    "title": "保费异议-百万医疗险",
    "objection_type": "price",
    "sales_stage": "objection",
    "scenario_context": "客户觉得每年保费6000元太贵",
    "customer": {
      "id": "cus_001",
      "name": "李伟"
    },
    "styles": [
      {
        "style": "professional",
        "style_label": "专业数据型",
        "content": "李先生，我理解您对保费的关注。让我用一组数据帮您分析...",
        "is_edited": false
      },
      {
        "style": "empathetic",
        "style_label": "共情故事型",
        "content": "李先生，完全理解您的顾虑。其实上个月我的一位客户...",
        "is_edited": false
      },
      {
        "style": "direct",
        "style_label": "直击痛点型",
        "content": "李先生，让我直接为您算一笔账...",
        "is_edited": false
      },
      {
        "style": "comparison",
        "style_label": "对比引导型",
        "content": "李先生，我们来做一个简单的对比...",
        "is_edited": false
      }
    ],
    "compliance_result": {
      "overall": "passed",
      "warnings": [],
      "violations": [],
      "checked_at": "2025-01-15T15:00:05+08:00"
    },
    "is_favorite": false,
    "created_by": {
      "id": "usr_a1b2c3d4",
      "name": "张明"
    },
    "created_at": "2025-01-15T15:00:00+08:00",
    "updated_at": "2025-01-15T15:00:05+08:00"
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

## 8. AI 陪练 API

> **权限**: `agent`、`supervisor`

### 8.1 陪练场景列表

```
GET /api/v1/training/scenarios
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `category` | string | — | 场景分类：`product_introduction`(产品介绍)、`objection_handling`(异议处理)、`needs_discovery`(需求挖掘)、`closing`(促单技巧)、`comprehensive`(综合场景) |
| `difficulty` | string | — | 难度：`easy`、`medium`、`hard` |
| `keyword` | string | — | 搜索场景名称 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "scn_001",
        "title": "百万医疗险 — 保费异议处理",
        "description": "客户认为百万医疗险保费过高，练习如何通过价值呈现化解价格异议。",
        "category": "objection_handling",
        "category_label": "异议处理",
        "difficulty": "medium",
        "estimated_duration_minutes": 15,
        "key_skills": ["异议化解", "价值呈现", "对比分析"],
        "customer_persona": {
          "name": "王先生",
          "age": 40,
          "occupation": "私企老板",
          "personality": "务实理性，对价格敏感"
        },
        "completion_count": 234,
        "avg_score": 76.5,
        "is_completed_by_me": true,
        "my_best_score": 82,
        "tags": ["热门", "推荐"]
      }
    ],
    "total": 15,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 8.2 陪练场景详情

```
GET /api/v1/training/scenarios/:id
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "scn_001",
    "title": "百万医疗险 — 保费异议处理",
    "description": "客户认为百万医疗险保费过高，练习如何通过价值呈现化解价格异议。",
    "category": "objection_handling",
    "difficulty": "medium",
    "estimated_duration_minutes": 15,
    "background": "客户王先生，40岁，私企老板。通过朋友介绍了解到了百万医疗险，但对每年6000元的保费表示太贵。他目前只有社保，之前从未购买过商业保险。",
    "customer_persona": {
      "name": "王先生",
      "age": 40,
      "occupation": "私企老板",
      "personality": "务实理性，对价格敏感",
      "pain_points": ["保费预算", "对保险不信任", "觉得社保就够了"],
      "buying_signals": ["关注家人健康", "朋友推荐", "有投保意愿但犹豫"]
    },
    "objectives": [
      "理解客户价格顾虑的真正原因",
      "通过对比分析展示产品价值",
      "化解保费异议并引导下一步"
    ],
    "success_criteria": [
      "成功识别客户真实顾虑",
      "使用了有效的价值呈现技巧",
      "话术符合合规要求",
      "自然地引导客户进入下一步"
    ],
    "ai_customer_config": {
      "response_style": "skeptical",
      "max_rounds": 15,
      "difficulty_modifiers": {
        "will_ask_competitor": true,
        "will_ask_for_discount": true,
        "objection_complexity": "multi_layer"
      }
    },
    "key_skills": ["异议化解", "价值呈现", "对比分析"],
    "completion_count": 234,
    "avg_score": 76.5
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 8.3 开始训练（SSE）

```
POST /api/v1/training/sessions
```

**Content-Type**: `application/json`
**Accept**: `text/event-stream`

**请求体**:

```json
{
  "scenario_id": "scn_001",
  "difficulty": "medium"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scenario_id` | string | ✅ | 场景 ID |
| `difficulty` | string | ❌ | 难度覆盖：`easy`、`medium`、`hard`，默认使用场景默认难度 |

**SSE 响应流**:

```
event: session_start
data: {"session_id": "ses_001", "scenario": {"id": "scn_001", "title": "百万医疗险 — 保费异议处理"}}

event: ai_customer_greeting
data: {
  "round": 0,
  "content": "你好，我是王先生。我朋友给我推荐了你们的百万医疗险，但是我看了下每年要6000块，说实话我觉得有点贵了。我有社保，感觉应该够用了吧？",
  "emotion": "skeptical",
  "emotion_label": "怀疑",
  "intent_signal": "价格顾虑 + 社保依赖"
}

event: session_ready
data: {"session_id": "ses_001", "status": "active", "max_rounds": 15}
```

---

### 8.4 训练对话（SSE）

```
POST /api/v1/training/sessions/:id/message
```

**Content-Type**: `application/json`
**Accept**: `text/event-stream`

**请求体**:

```json
{
  "content": "王先生您好，非常感谢您朋友的推荐。我完全理解您的顾虑，很多客户一开始也有同样的想法。您知道吗，其实社保的报销是有封顶线的..."
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | string | ✅ | 代理人发送的消息，最大 1000 字 |

**SSE 响应流**:

```
event: message_received
data: {"round": 1, "agent_message_id": "msg_001"}

event: ai_thinking
data: {"status": "thinking"}

event: ai_customer_reply
data: {
  "round": 1,
  "content": "社保封顶线我知道，但是我身体挺好的，住医院的概率不大吧？而且万一真的住院了，6000块一年攒下来也不少了。",
  "emotion": "doubtful",
  "emotion_label": "犹豫",
  "intent_signal": "健康自信 + 机会成本考虑",
  "objection_detected": "低概率事件不值得投保"
}

event: coaching_hint
data: {
  "type": "suggestion",
  "hint": "客户表达了「健康自信」，这是典型的乐观偏差。可以尝试用具体的医疗费用数据来唤醒风险意识。",
  "skill_tag": "风险唤醒"
}
```

---

### 8.5 完成训练

```
POST /api/v1/training/sessions/:id/complete
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "session_id": "ses_001",
    "scenario": {
      "id": "scn_001",
      "title": "百万医疗险 — 保费异议处理"
    },
    "duration_seconds": 420,
    "total_rounds": 8,
    "scores": {
      "professionalism": {
        "score": 85,
        "label": "专业度",
        "details": "话术使用规范，产品知识准确，但在条款细节上可进一步深入"
      },
      "communication": {
        "score": 78,
        "label": "沟通技巧",
        "details": "倾听能力良好，共情表达自然，但转折衔接可更流畅"
      },
      "closing_ability": {
        "score": 70,
        "label": "促单能力",
        "details": "未能有效引导客户做出明确承诺，缺少明确的 next step"
      }
    },
    "overall_score": 77.7,
    "overall_rating": "good",
    "overall_rating_label": "良好",
    "strengths": [
      "产品知识扎实",
      "能灵活运用对比分析技巧",
      "共情表达自然"
    ],
    "improvements": [
      "需要加强促单环节的练习",
      "注意在异议处理中使用更多开放式提问",
      "建议练习多种开场方式"
    ],
    "compliance_result": {
      "overall": "passed",
      "violations": 0,
      "warnings": 1
    },
    "conversation_summary": [
      {
        "round": 1,
        "agent_summary": "回应了客户的社保顾虑，引出了封顶线话题",
        "score": 3,
        "max_score": 5
      }
    ],
    "completed_at": "2025-01-15T16:30:00+08:00"
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 8.6 训练记录列表

```
GET /api/v1/training/sessions
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `scenario_id` | string | — | 场景 ID 筛选 |
| `status` | string | — | 状态：`active`、`completed`、`abandoned` |
| `min_score` | int | — | 最低分数筛选 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |
| `sort_by` | string | `created_at` | 排序字段 |
| `sort_order` | string | `desc` | 排序方向 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "ses_001",
        "scenario": {
          "id": "scn_001",
          "title": "百万医疗险 — 保费异议处理"
        },
        "difficulty": "medium",
        "overall_score": 77.7,
        "overall_rating": "good",
        "total_rounds": 8,
        "duration_seconds": 420,
        "status": "completed",
        "completed_at": "2025-01-15T16:30:00+08:00",
        "created_at": "2025-01-15T16:23:00+08:00"
      }
    ],
    "total": 25,
    "page": 1,
    "page_size": 20,
    "total_pages": 2
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 8.7 训练记录详情

```
GET /api/v1/training/sessions/:id
```

**成功响应** `200`:

返回与 8.5 完成训练相同的完整数据结构，包括所有对话轮次的详细记录和评分。

---

### 8.8 训练统计

```
GET /api/v1/training/stats
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `period` | string | `month` | 统计周期：`week`、`month`、`quarter`、`year` |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "period": "month",
    "total_sessions": 28,
    "completed_sessions": 24,
    "completion_rate": 85.7,
    "avg_score": 76.3,
    "best_score": 92,
    "score_trend": [
      {"date": "2025-01-01", "avg_score": 72.0},
      {"date": "2025-01-08", "avg_score": 74.5},
      {"date": "2025-01-15", "avg_score": 76.3}
    ],
    "category_breakdown": [
      {"category": "objection_handling", "count": 12, "avg_score": 78.0},
      {"category": "product_introduction", "count": 8, "avg_score": 74.5},
      {"category": "needs_discovery", "count": 5, "avg_score": 73.0},
      {"category": "closing", "count": 3, "avg_score": 80.0}
    ],
    "practice_streak": 5,
    "total_practice_minutes": 180
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 8.9 能力雷达图

```
GET /api/v1/training/radar
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "dimensions": [
      {
        "skill": "产品知识",
        "score": 85,
        "max_score": 100,
        "trend": "+3",
        "level": "proficient",
        "level_label": "熟练"
      },
      {
        "skill": "沟通技巧",
        "score": 78,
        "max_score": 100,
        "trend": "+5",
        "level": "proficient",
        "level_label": "熟练"
      },
      {
        "skill": "异议处理",
        "score": 72,
        "max_score": 100,
        "trend": "+8",
        "level": "intermediate",
        "level_label": "中级"
      },
      {
        "skill": "需求挖掘",
        "score": 68,
        "max_score": 100,
        "trend": "+2",
        "level": "intermediate",
        "level_label": "中级"
      },
      {
        "skill": "促单能力",
        "score": 65,
        "max_score": 100,
        "trend": "-1",
        "level": "intermediate",
        "level_label": "中级"
      },
      {
        "skill": "合规意识",
        "score": 90,
        "max_score": 100,
        "trend": "+2",
        "level": "expert",
        "level_label": "精通"
      }
    ],
    "overall_score": 76.3,
    "last_updated": "2025-01-15T16:30:00+08:00"
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

## 9. AI 社区 API

> **权限**: `agent`、`supervisor`

### 9.1 社区帖子列表

```
GET /api/v1/community/posts
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | string | — | 搜索标题和内容 |
| `category` | string | — | 分类：`experience`(实战经验)、`knowledge`(知识分享)、`question`(求助提问)、`discussion`(讨论)、`script`(优秀话术) |
| `tags` | string[] | — | 标签筛选 |
| `sort_by` | string | `created_at` | 排序字段：`created_at`、`likes_count`、`comments_count`、`views_count` |
| `sort_order` | string | `desc` | 排序方向 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "post_001",
        "title": "分享：如何用三个问题快速了解客户需求",
        "author": {
          "id": "usr_b2c3d4e5",
          "name": "李小红",
          "avatar": "https://cdn.example.com/avatars/b2c3.jpg",
          "role": "supervisor"
        },
        "category": "experience",
        "category_label": "实战经验",
        "summary": "经过大量实践，我总结了三个核心问题，可以帮助代理人快速了解客户的保障需求和预算...",
        "tags": ["需求挖掘", "实战技巧", "方法论"],
        "views_count": 456,
        "likes_count": 89,
        "comments_count": 23,
        "is_pinned": false,
        "is_recommended": true,
        "is_liked_by_me": false,
        "is_favorited_by_me": false,
        "created_at": "2025-01-14T10:00:00+08:00"
      }
    ],
    "total": 156,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 9.2 帖子详情

```
GET /api/v1/community/posts/:id
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "post_001",
    "title": "分享：如何用三个问题快速了解客户需求",
    "content": "经过大量实践，我总结了三个核心问题...\n\n## 第一个问题：保障认知\n\"您目前有没有给自己或家人配置过商业保险呢？\"...\n\n## 第二个问题：关注重点\n\"如果您现在要选一份保险，最看重的是什么？\"...",
    "author": {
      "id": "usr_b2c3d4e5",
      "name": "李小红",
      "avatar": "https://cdn.example.com/avatars/b2c3.jpg",
      "role": "supervisor",
      "organization": "华东区第一营业部"
    },
    "category": "experience",
    "tags": ["需求挖掘", "实战技巧", "方法论"],
    "views_count": 457,
    "likes_count": 89,
    "comments_count": 23,
    "is_pinned": false,
    "is_recommended": true,
    "is_liked_by_me": false,
    "is_favorited_by_me": false,
    "created_at": "2025-01-14T10:00:00+08:00",
    "updated_at": "2025-01-14T10:00:00+08:00"
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 9.3 发布帖子

```
POST /api/v1/community/posts
```

**请求体**:

```json
{
  "title": "我的百万医疗险成交经验分享",
  "content": "上周成功签下一单百万医疗险，分享一下我的经验...",
  "category": "experience",
  "tags": ["百万医疗", "成交案例", "经验分享"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 标题，最大 100 字 |
| `content` | string | ✅ | 正文，最大 5000 字，支持 Markdown |
| `category` | string | ✅ | 分类 |
| `tags` | string[] | ❌ | 标签，最多 5 个 |

**成功响应** `201`:

```json
{
  "success": true,
  "data": {
    "id": "post_new_001",
    "title": "我的百万医疗险成交经验分享",
    "status": "pending_review",
    "created_at": "2025-01-15T17:00:00+08:00"
  },
  "message": "帖子已提交，等待审核",
  "request_id": "req_xxx"
}
```

---

### 9.4 编辑帖子

```
PUT /api/v1/community/posts/:id
```

> 仅作者本人可编辑。

**请求体**: 同 9.3（所有字段可选）。

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "post_001",
    "status": "pending_review",
    "updated_at": "2025-01-15T17:00:00+08:00"
  },
  "message": "帖子已更新，重新审核中",
  "request_id": "req_xxx"
}
```

---

### 9.5 删除帖子

```
DELETE /api/v1/community/posts/:id
```

> 仅作者本人或管理员可删除。

**成功响应** `200`:

```json
{
  "success": true,
  "data": null,
  "message": "帖子已删除",
  "request_id": "req_xxx"
}
```

---

### 9.6 点赞帖子

```
POST /api/v1/community/posts/:id/like
```

> 支持切换（再次调用取消点赞）。

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "is_liked": true,
    "likes_count": 90
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 9.7 收藏帖子

```
POST /api/v1/community/posts/:id/favorite
```

> 支持切换（再次调用取消收藏）。

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "is_favorited": true,
    "favorites_count": 15
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 9.8 评论帖子

```
POST /api/v1/community/posts/:id/comments
```

**请求体**:

```json
{
  "content": "非常实用的分享！我也经常用类似的方法，补充一点：在问第三个问题时可以结合具体产品来引导。",
  "parent_comment_id": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | string | ✅ | 评论内容，最大 500 字 |
| `parent_comment_id` | string | ❌ | 父评论 ID，用于回复 |

**成功响应** `201`:

```json
{
  "success": true,
  "data": {
    "id": "cmt_001",
    "content": "非常实用的分享！...",
    "author": {
      "id": "usr_a1b2c3d4",
      "name": "张明"
    },
    "parent_comment_id": null,
    "created_at": "2025-01-15T17:30:00+08:00"
  },
  "message": "评论成功",
  "request_id": "req_xxx"
}
```

---

### 9.9 帖子评论列表

```
GET /api/v1/community/posts/:id/comments
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |
| `sort_by` | string | `created_at` | 排序字段 |
| `sort_order` | string | `asc` | 评论默认按时间正序 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "cmt_001",
        "content": "非常实用的分享！...",
        "author": {
          "id": "usr_a1b2c3d4",
          "name": "张明",
          "avatar": "https://cdn.example.com/avatars/a1b2.jpg"
        },
        "likes_count": 5,
        "is_liked_by_me": false,
        "replies": [],
        "created_at": "2025-01-15T17:30:00+08:00"
      }
    ],
    "total": 23,
    "page": 1,
    "page_size": 20,
    "total_pages": 2
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 9.10 AI 摘要（SSE）

```
GET /api/v1/community/posts/{post_id}/ai-summary
```

**说明**: 生产模式从数据库读取帖子（`PostRepository`），经 AI Gateway 流式生成摘要后持久化到 `post.ai_summary`。

**SSE 响应流（成功）**:

```
event: summary_start
data: {"post_id": "..."}

event: token
data: {"content": "本文介绍了", "index": 0}

event: summary_complete
data: {"summary": "本文介绍了……"}
```

**失败行为**:

- AI 失败 / 超时 / 返回空内容 → 仅发送 `error` 事件（不发送 `summary_complete`），**不保存错误文本**，已有摘要保持不变。
- 帖子不存在 / 已删除 → `error` 事件（`帖子不存在`）。

```
event: error
data: {"message": "AI 摘要生成失败，请稍后重试。"}
```

**权限**: 社区帖子为公共内容，任意登录用户可触发摘要；`post_id` 不存在或已软删除时返回 `error`。


## 10. 我的成长 API

> **权限**: 登录用户（JWT Bearer）。排行榜响应受组织可见范围限制（RBAC）。

### 10.1 成长概览

```
GET /api/v1/growth/overview
```

**说明**: 生产模式从数据库真实聚合：月度统计（本月互动/成交保单/待跟进客户/AI 使用次数）、最近 7 天互动趋势、能力评分（由陪练评分映射）、成长等级与经验值（由完成陪练 + 解锁成就推导）。

**成功响应** `200`:

```json
{
  "monthly_stats": [
    {"label": "本月互动", "value": "12", "unit": "次", "change": "+3 较上月", "up": true},
    {"label": "成交保单", "value": "2", "unit": "件", "change": "1个高意向", "up": true},
    {"label": "待跟进客户", "value": "5", "unit": "个", "change": "待处理", "up": true},
    {"label": "AI 使用次数", "value": "34", "unit": "次", "change": "本月累计", "up": true}
  ],
  "weekly_trend": [
    {"day": "周一", "calls": 3, "deals": 0}
  ],
  "ability_scores": [
    {"label": "产品知识", "score": 85},
    {"label": "沟通技巧", "score": 78}
  ],
  "learning_courses": [],
  "level": 1,
  "level_name": "新人代理人",
  "exp_current": 60,
  "exp_next": 500,
  "total_exp": 60
}
```

---

### 10.2 课程详情

```
GET /api/v1/growth/courses/{course_id}
```

**说明**: Demo 模式返回静态课程；生产模式数据库暂无课程表，返回 `null`（不伪造数据，待课程体系落库）。

**成功响应** `200`（Demo）:

```json
{
  "id": "course-001",
  "title": "重疾险产品知识进阶",
  "description": "深入学习重疾险产品条款、保障范围、理赔条件，掌握核心卖点。",
  "category": "产品知识",
  "progress": 85,
  "total_lessons": 14,
  "completed_lessons": 12,
  "status": "进行中",
  "lessons": []
}
```

**生产模式**: `200` + `null`。

---

### 10.3 排行榜

```
GET /api/v1/growth/leaderboard?period=month
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `period` | string | `month` | 排行榜周期：`week` / `month` / `quarter` |

**组织可见范围（RBAC）**: 生产模式按当前用户角色 level 限制排行数据可见范围，不扩大数据暴露：

| 角色 | level | 可见范围 |
|------|:---:|---------|
| SYSTEM_ADMIN / HQ_ADMIN | ≥90 | 全部组织 |
| BRANCH_ADMIN | ≥80 | 本组织 + 直接子组织 |
| TEAM_LEADER / AGENT / 其他 | <80 | 仅本组织（优先 team_id） |

**打分规则**: 真实活动聚合 —— 成交客户 ×100 + 解锁成就 ×50 + 完成陪练 ×10（仅统计 >0 的用户）。

**成功响应** `200`:

```json
{
  "period": "month",
  "leaderboard": [
    {"rank": 1, "user_name": "林思远", "org_name": "华东区第一营业部", "score": 150, "avatar": ""}
  ],
  "my_rank": {"rank": 1, "user_name": "林思远", "org_name": "华东区第一营业部", "score": 150, "avatar": ""}
}
```

---

### 10.4 成就列表

```
GET /api/v1/growth/achievements
```

**说明**: 生产模式按当前用户 ID 查询成就（已解锁 + 未解锁），用户数据隔离。

**成功响应** `200`:

```json
{
  "unlocked": [
    {"id": "...", "name": "首次完成陪练", "description": "...", "icon": "🏅", "unlocked_at": "2026-08-01T10:00:00+08:00", "is_unlocked": true, "category": "sales"}
  ],
  "locked": []
}
```

## 11. 消息中心 API

> **权限**: 所有已认证用户

### 11.1 通知列表

```
GET /api/v1/notifications
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | — | 通知类型：`system`(系统通知)、`follow_up`(跟进提醒)、`ai_suggestion`(AI建议)、`community`(社区互动)、`training`(训练完成)、`compliance`(合规提醒) |
| `is_read` | bool | — | 已读/未读筛选 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "ntf_001",
        "type": "follow_up",
        "type_label": "跟进提醒",
        "title": "客户李伟的跟进计划即将到期",
        "content": "您与客户李伟的跟进计划（电话回访）安排在今天 10:00，请及时处理。",
        "action_url": "/customers/cus_001",
        "is_read": false,
        "created_at": "2025-01-16T09:00:00+08:00"
      }
    ],
    "total": 28,
    "page": 1,
    "page_size": 20,
    "total_pages": 2
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 11.2 未读数量

```
GET /api/v1/notifications/unread-count
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "total_unread": 8,
    "breakdown": {
      "follow_up": 3,
      "ai_suggestion": 2,
      "community": 1,
      "system": 2
    }
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 11.3 标记已读

```
POST /api/v1/notifications/:id/read
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "ntf_001",
    "is_read": true
  },
  "message": "",
  "request_id": "req_xxx"
}
```

---

### 11.4 全部标记已读

```
POST /api/v1/notifications/read-all
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "marked_count": 8
  },
  "message": "已全部标记为已读",
  "request_id": "req_xxx"
}
```

---

## 12. 管理后台 API

> **权限**: `admin`

### 12.1 用户管理

#### 获取用户列表

```
GET /api/v1/admin/users
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | string | — | 搜索姓名、手机号 |
| `role` | string | — | 角色筛选 |
| `status` | string | — | 状态：`active`、`disabled` |
| `organization_id` | string | — | 部门筛选 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |

#### 创建用户

```
POST /api/v1/admin/users
```

**请求体**:

```json
{
  "name": "赵六",
  "phone": "13900001111",
  "role": "agent",
  "organization_id": "org_001",
  "initial_password": "Abc12345!"
}
```

#### 更新用户

```
PUT /api/v1/admin/users/:id
```

#### 禁用用户

```
POST /api/v1/admin/users/:id/disable
```

**请求体**:

```json
{
  "reason": "违反社区规范"
}
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "usr_c3d4e5f6",
    "status": "disabled",
    "disabled_at": "2025-01-15T18:00:00+08:00"
  },
  "message": "用户已禁用",
  "request_id": "req_xxx"
}
```

---

### 12.2 客户管理

#### 获取全部客户

```
GET /api/v1/admin/customers
```

> 管理员可查看所有客户的完整数据，查询参数同 6.1，额外增加：

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | string | 按代理人筛选 |
| `organization_id` | string | 按部门筛选 |

#### 分配客户

```
POST /api/v1/admin/customers/:id/assign
```

**请求体**:

```json
{
  "agent_id": "usr_a1b2c3d4",
  "reason": "原代理人离职，客户转移"
}
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "customer_id": "cus_001",
    "previous_agent": "usr_b2c3d4e5",
    "new_agent": "usr_a1b2c3d4",
    "assigned_at": "2025-01-15T18:00:00+08:00"
  },
  "message": "客户已重新分配",
  "request_id": "req_xxx"
}
```

---

### 12.3 知识库管理

#### 文档列表

```
GET /api/v1/admin/knowledge/documents
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | string | — | 状态：`uploaded`、`parsing`、`parsed`、`reviewing`、`published`、`expired` |
| `category` | string | — | 分类：`product`、`policy`、`faq`、`training`、`compliance` |
| `keyword` | string | — | 搜索文档名称 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |

#### 上传文档

```
POST /api/v1/admin/knowledge/documents/upload
```

**Content-Type**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | ✅ | 文件，支持 PDF、DOCX、TXT、MD，最大 50MB |
| `category` | string | ✅ | 文档分类 |
| `title` | string | ✅ | 文档标题 |
| `description` | string | ❌ | 文档描述 |
| `tags` | string[] | ❌ | 标签 |
| `product_ids` | string[] | ❌ | 关联产品 ID |

**成功响应** `201`:

```json
{
  "success": true,
  "data": {
    "id": "doc_new_001",
    "title": "安诊保百万医疗险产品条款 v4.0",
    "status": "uploaded",
    "file_size": 2048576,
    "created_at": "2025-01-15T18:30:00+08:00"
  },
  "message": "文档上传成功，请启动解析",
  "request_id": "req_xxx"
}
```

#### 解析文档

```
POST /api/v1/admin/knowledge/documents/:id/parse
```

**请求体**:

```json
{
  "chunk_strategy": "semantic",
  "chunk_size": 512,
  "chunk_overlap": 50
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `chunk_strategy` | string | ❌ | 分块策略：`fixed`(固定长度)、`semantic`(语义分块)，默认 `semantic` |
| `chunk_size` | int | ❌ | 分块大小（token 数），默认 512 |
| `chunk_overlap` | int | ❌ | 重叠 token 数，默认 50 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "document_id": "doc_new_001",
    "status": "parsing",
    "estimated_chunks": 45,
    "started_at": "2025-01-15T18:31:00+08:00"
  },
  "message": "文档解析已启动",
  "request_id": "req_xxx"
}
```

#### 查看文档分块

```
GET /api/v1/admin/knowledge/documents/:id/chunks
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数 |
| `status` | string | — | 分块状态：`pending_review`、`approved`、`rejected` |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "chunk_id": "chk_001",
        "content": "第一条 保险责任：在本合同保险期间内，被保险人因意外伤害或等待期后因疾病...",
        "token_count": 486,
        "position": 1,
        "status": "approved",
        "reviewed_by": {
          "id": "usr_admin_001",
          "name": "管理员"
        },
        "reviewed_at": "2025-01-15T19:00:00+08:00"
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  },
  "message": "",
  "request_id": "req_xxx"
}
```

#### 编辑分块

```
PUT /api/v1/admin/knowledge/documents/:id/chunks/:chunk_id
```

**请求体**:

```json
{
  "content": "修改后的分块内容...",
  "status": "pending_review"
}
```

#### 提交审核

```
POST /api/v1/admin/knowledge/documents/:id/submit-review
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "document_id": "doc_new_001",
    "status": "reviewing",
    "total_chunks": 45,
    "pending_review_chunks": 12,
    "submitted_at": "2025-01-15T19:00:00+08:00"
  },
  "message": "已提交审核",
  "request_id": "req_xxx"
}
```

#### 发布文档

```
POST /api/v1/admin/knowledge/documents/:id/publish
```

> 将审核通过的文档发布到知识库，执行 Embedding 后可被 AI 检索。

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "document_id": "doc_new_001",
    "status": "published",
    "embedded_chunks": 45,
    "published_at": "2025-01-15T19:30:00+08:00"
  },
  "message": "文档已发布到知识库",
  "request_id": "req_xxx"
}
```

#### 文档过期

```
POST /api/v1/admin/knowledge/documents/:id/expire
```

**请求体**:

```json
{
  "reason": "产品条款已更新为新版本"
}
```

> 过期文档不再被 AI 检索，但保留历史记录。

#### 重新分块

```
POST /api/v1/admin/knowledge/documents/:id/re-chunk
```

**请求体**:

```json
{
  "chunk_strategy": "semantic",
  "chunk_size": 1024,
  "chunk_overlap": 100
}
```

> 重新执行文档分块，已有 Embedding 数据将被清除。

#### 重新 Embedding

```
POST /api/v1/admin/knowledge/documents/:id/re-embed
```

> 使用最新的 Embedding 模型重新生成向量，通常在模型升级后执行。

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "document_id": "doc_new_001",
    "status": "embedding",
    "total_chunks": 45,
    "started_at": "2025-01-15T20:00:00+08:00"
  },
  "message": "重新 Embedding 已启动",
  "request_id": "req_xxx"
}
```

---

### 12.4 陪练场景管理

#### 场景 CRUD

```
GET    /api/v1/admin/training/scenarios
POST   /api/v1/admin/training/scenarios
PUT    /api/v1/admin/training/scenarios/:id
DELETE /api/v1/admin/training/scenarios/:id
```

**创建/更新场景请求体**:

```json
{
  "title": "年金险 — 养老规划异议处理",
  "description": "练习如何应对客户对年金险收益不确定的顾虑...",
  "category": "objection_handling",
  "difficulty": "hard",
  "background": "客户张女士，50岁，即将退休...",
  "customer_persona": {
    "name": "张女士",
    "age": 50,
    "occupation": "国企员工",
    "personality": "保守稳健",
    "pain_points": ["收益不确定", "通货膨胀"],
    "buying_signals": ["关注养老", "有退休规划"]
  },
  "objectives": ["分析客户养老需求", "展示年金险的确定性价值", "制定合理的养老方案"],
  "success_criteria": ["正确分析养老缺口", "有效展示收益演示", "合规使用收益表述"],
  "ai_customer_config": {
    "response_style": "cautious",
    "max_rounds": 12,
    "difficulty_modifiers": {
      "will_ask_competitor": true,
      "will_ask_for_discount": false,
      "objection_complexity": "deep"
    }
  },
  "tags": ["年金险", "养老", "进阶"],
  "estimated_duration_minutes": 20
}
```

#### 发布场景

```
POST /api/v1/admin/training/scenarios/:id/publish
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "scn_new_001",
    "status": "published",
    "published_at": "2025-01-15T20:30:00+08:00"
  },
  "message": "场景已发布",
  "request_id": "req_xxx"
}
```

---

### 12.5 话术库管理

#### 获取话术列表（管理视角）

```
GET /api/v1/admin/scripts
```

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string | 审核状态：`pending`、`approved`、`rejected` |
| `keyword` | string | 搜索 |
| `objection_type` | string | 异议类型 |
| `agent_id` | string | 按创建人筛选 |
| `page` | int | 页码 |
| `page_size` | int | 每页条数 |

#### 审批话术

```
POST /api/v1/admin/scripts/:id/approve
```

**请求体**:

```json
{
  "action": "approve",
  "comment": "话术合规，内容专业，批准发布"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | ✅ | 操作：`approve`（通过）、`reject`（驳回） |
| `comment` | string | ❌ | 审批意见 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "id": "scr_001",
    "status": "approved",
    "reviewed_by": {
      "id": "usr_admin_001",
      "name": "管理员"
    },
    "reviewed_at": "2025-01-15T21:00:00+08:00"
  },
  "message": "话术已审批通过",
  "request_id": "req_xxx"
}
```

---

### 12.6 社区管理

#### 获取全部帖子（管理视角）

```
GET /api/v1/admin/community/posts
```

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string | 状态：`pending_review`、`published`、`hidden`、`reported` |
| `keyword` | string | 搜索 |
| `category` | string | 分类 |
| `author_id` | string | 按作者筛选 |
| `page` | int | 页码 |
| `page_size` | int | 每页条数 |

#### 置顶帖子

```
POST /api/v1/admin/community/posts/:id/pin
```

**请求体**:

```json
{
  "is_pinned": true,
  "pin_expiry": "2025-01-30T23:59:59+08:00"
}
```

#### 推荐帖子

```
POST /api/v1/admin/community/posts/:id/recommend
```

**请求体**:

```json
{
  "is_recommended": true,
  "recommend_reason": "实战经验丰富，值得全员学习"
}
```

#### 删除帖子（管理）

```
DELETE /api/v1/admin/community/posts/:id
```

**请求体**:

```json
{
  "reason": "内容违规，包含不实信息"
}
```

---

### 12.7 合规中心

#### 合规规则管理

```
GET  /api/v1/admin/compliance/rules
POST /api/v1/admin/compliance/rules
PUT  /api/v1/admin/compliance/rules/:id
```

**规则对象**:

```json
{
  "id": "rule_001",
  "name": "收益承诺禁止",
  "description": "禁止在话术中使用确定性的收益承诺表述",
  "category": "regulatory",
  "severity": "violation",
  "severity_label": "违规",
  "keywords": ["保证收益", "稳赚不赔", "一定赚钱", "承诺回报"],
  "patterns": ["收益.*保证", "回报.*确定"],
  "is_active": true,
  "created_at": "2025-01-01T10:00:00+08:00"
}
```

#### 合规审核列表

```
GET /api/v1/admin/compliance/reviews
```

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string | 状态：`pending`、`approved`、`rejected` |
| `type` | string | 类型：`script`(话术审核)、`community_post`(社区帖子审核) |
| `priority` | string | 优先级：`high`、`medium`、`low` |
| `page` | int | 页码 |
| `page_size` | int | 每页条数 |

#### 处理审核

```
POST /api/v1/admin/compliance/reviews/:id/process
```

**请求体**:

```json
{
  "action": "approved",
  "comment": "话术内容合规，准予使用",
  "conditions": ["需注意收益表述使用演示数据而非承诺"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | ✅ | 处理结果：`approved`、`rejected`、`needs_revision` |
| `comment` | string | ✅ | 处理意见 |
| `conditions` | string[] | ❌ | 附加条件（仅 `approved` 时可用） |

---

### 12.8 数据看板

#### 总览数据

```
GET /api/v1/admin/analytics/overview
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `period` | string | `month` | 统计周期：`week`、`month`、`quarter`、`year` |
| `organization_id` | string | — | 按部门筛选 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "period": "month",
    "user_stats": {
      "total_users": 356,
      "active_users": 280,
      "new_users": 12,
      "active_rate": 78.7
    },
    "customer_stats": {
      "total_customers": 12580,
      "new_customers": 856,
      "high_intent": 1245,
      "conversion_rate": 15.3
    },
    "ai_stats": {
      "total_interactions": 8934,
      "satisfaction_rate": 86.2,
      "avg_response_time_ms": 1200
    },
    "training_stats": {
      "total_sessions": 1234,
      "avg_score": 76.8,
      "completion_rate": 82.5
    },
    "community_stats": {
      "total_posts": 234,
      "total_comments": 1567,
      "active_contributors": 89
    }
  },
  "message": "",
  "request_id": "req_xxx"
}
```

#### AI 使用分析

```
GET /api/v1/admin/analytics/ai-usage
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "period": "month",
    "total_calls": 8934,
    "feature_breakdown": [
      {"feature": "product_qa", "count": 3560, "percentage": 39.9},
      {"feature": "script_generate", "count": 2340, "percentage": 26.2},
      {"feature": "customer_analysis", "count": 1780, "percentage": 19.9},
      {"feature": "training", "count": 1254, "percentage": 14.0}
    ],
    "top_users": [
      {"user_id": "usr_a1b2", "name": "张明", "usage_count": 156},
      {"user_id": "usr_b2c3", "name": "李小红", "usage_count": 134}
    ],
    "error_rate": 2.3,
    "avg_latency_ms": 1200,
    "token_usage": {
      "total_input_tokens": 4500000,
      "total_output_tokens": 2300000,
      "total_tokens": 6800000
    }
  },
  "message": "",
  "request_id": "req_xxx"
}
```

#### 训练分析

```
GET /api/v1/admin/analytics/training
```

#### 社区分析

```
GET /api/v1/admin/analytics/community
```

---

### 12.9 审计日志

#### 查询审计日志

```
GET /api/v1/admin/audit-logs
```

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 操作人 ID |
| `action` | string | 操作类型 |
| `resource_type` | string | 资源类型 |
| `resource_id` | string | 资源 ID |
| `start_time` | string | 开始时间（ISO 8601） |
| `end_time` | string | 结束时间（ISO 8601） |
| `page` | int | 页码 |
| `page_size` | int | 每页条数，最大 100 |

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "log_001",
        "user": {
          "id": "usr_a1b2c3d4",
          "name": "张明",
          "role": "agent"
        },
        "action": "customer.update",
        "resource_type": "customer",
        "resource_id": "cus_001",
        "description": "更新客户李伟的阶段为「需求分析」",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0...)",
        "request_id": "req_abc123",
        "created_at": "2025-01-15T16:00:00+08:00"
      }
    ],
    "total": 5678,
    "page": 1,
    "page_size": 50,
    "total_pages": 114
  },
  "message": "",
  "request_id": "req_xxx"
}
```

#### 导出审计日志

```
POST /api/v1/admin/audit-logs/export
```

**请求体**:

```json
{
  "filters": {
    "start_time": "2025-01-01T00:00:00+08:00",
    "end_time": "2025-01-31T23:59:59+08:00",
    "action": "customer.*"
  },
  "format": "xlsx"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `filters` | object | ❌ | 筛选条件，同查询参数 |
| `format` | string | ❌ | 导出格式：`xlsx`、`csv`，默认 `xlsx` |

**成功响应** `200`:

返回文件流，响应头：

```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="audit_logs_2025-01.xlsx"
```

---

### 12.10 系统设置

#### 获取系统设置

```
GET /api/v1/admin/settings
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "ai": {
      "default_model": "gpt-4",
      "max_tokens": 4096,
      "temperature": 0.7,
      "timeout_seconds": 30,
      "rate_limit_per_minute": 20
    },
    "rag": {
      "embedding_model": "text-embedding-3-small",
      "default_chunk_size": 512,
      "default_chunk_overlap": 50,
      "top_k": 5,
      "similarity_threshold": 0.7
    },
    "compliance": {
      "auto_check_enabled": true,
      "severity_levels": ["warning", "violation"],
      "auto_reject_violations": true
    },
    "notification": {
      "follow_up_reminder_hours": 24,
      "inactive_customer_days": 30
    },
    "community": {
      "post_review_enabled": true,
      "max_tags_per_post": 5,
      "comment_max_length": 500
    }
  },
  "message": "",
  "request_id": "req_xxx"
}
```

#### 更新系统设置

```
PUT /api/v1/admin/settings
```

> 仅需传入需要修改的设置分组。

**请求体**:

```json
{
  "ai": {
    "max_tokens": 8192,
    "temperature": 0.6
  }
}
```

**成功响应** `200`:

```json
{
  "success": true,
  "data": {
    "updated_keys": ["ai.max_tokens", "ai.temperature"]
  },
  "message": "系统设置已更新",
  "request_id": "req_xxx"
}
```

---

## 13. SSE 流式响应规范

### 13.1 连接要求

- **协议**: Server-Sent Events (SSE)，使用 `text/event-stream` Content-Type
- **客户端请求头**: `Accept: text/event-stream`
- **超时**: 连接保持 **最长 5 分钟**，期间持续推送事件
- **心跳**: 无数据推送时，每 **15 秒** 发送一次 `ping` 事件
- **重连**: 客户端断连后，使用 `Last-Event-ID` 头恢复断点

### 13.2 标准 SSE 事件格式

每个事件包含 `event` 类型和 `data` JSON 数据：

```
event: <event_type>
data: <json_payload>

```

> 事件之间以空行分隔，`data` 字段为 JSON 字符串。

### 13.3 通用事件类型

#### 心跳事件

```
event: ping
data: {"timestamp": "2025-01-15T16:30:00+08:00"}
```

#### 错误事件

```
event: error
data: {"code": "AI_001", "message": "AI服务不可用，请稍后重试"}
```

> 收到 `error` 事件后，流将关闭。

#### 连接建立确认

```
event: connected
data: {"request_id": "req_xxx", "session_id": "ses_001"}
```

### 13.4 产品问答 SSE 事件

| 事件类型 | 说明 | data 结构 |
|----------|------|-----------|
| `connected` | 连接建立 | `{ request_id }` |
| `message_start` | 开始生成回答 | `{ conversation_id, message_id }` |
| `token` | 文本 token 增量 | `{ content }` |
| `related_products` | 关联产品推荐 | `{ products: [{id, name, category}] }` |
| `reference_sources` | 知识库来源引用 | `{ sources: [{document_id, title, relevance, chunk_text}] }` |
| `message_complete` | 回答生成完成 | `{ message_id, token_count, sources_count }` |

### 13.5 客户分析 SSE 事件

| 事件类型 | 说明 | data 结构 |
|----------|------|-----------|
| `connected` | 连接建立 | `{ request_id }` |
| `analysis_start` | 开始分析 | `{ customer_id, analysis_id }` |
| `step` | 分析步骤进度 | `{ step, label, progress }` |
| `result_risk_profile` | 风险画像结果 | `{ risk_profile, risk_factors, risk_details }` |
| `result_recommendations` | 产品推荐结果 | `{ products: [{id, name, match_score, reason}], communication_strategy }` |
| `analysis_complete` | 分析完成 | `{ analysis_id, token_count, duration_ms }` |

### 13.6 话术生成 SSE 事件

| 事件类型 | 说明 | data 结构 |
|----------|------|-----------|
| `connected` | 连接建立 | `{ request_id }` |
| `generation_start` | 开始生成 | `{ generation_id }` |
| `step` | 生成步骤进度 | `{ step, label, progress }` |
| `script_style` | 单个风格话术结果 | `{ style, style_label, content, compliance_check: {passed, warnings, violations} }` |
| `compliance_summary` | 合规检查汇总 | `{ total_checks, passed, warnings, violations }` |
| `generation_complete` | 生成完成 | `{ generation_id, script_id, token_count, duration_ms }` |

### 13.7 陪练 SSE 事件

| 事件类型 | 说明 | data 结构 |
|----------|------|-----------|
| `connected` | 连接建立 | `{ request_id }` |
| `session_start` | 训练开始 | `{ session_id, scenario }` |
| `ai_customer_greeting` | AI 客户开场 | `{ round, content, emotion, emotion_label, intent_signal }` |
| `session_ready` | 训练就绪 | `{ session_id, status, max_rounds }` |
| `message_received` | 用户消息已接收 | `{ round, agent_message_id }` |
| `ai_thinking` | AI 思考中 | `{ status }` |
| `ai_customer_reply` | AI 客户回复 | `{ round, content, emotion, emotion_label, intent_signal, objection_detected? }` |
| `coaching_hint` | 教练提示 | `{ type, hint, skill_tag }` |

### 13.8 异常处理

| 场景 | 处理方式 |
|------|----------|
| AI 服务不可用 | 发送 `error` 事件（`AI_001`），关闭流 |
| AI 生成超时（>30s） | 发送 `error` 事件（`AI_002`），关闭流 |
| Token 过期 | 发送 `error` 事件（`AUTH_003`），关闭流 |
| 客户端断连 | 服务端自动释放资源，记录日志 |
| 生成内容异常 | 发送 `error` 事件（`AI_003`），关闭流 |

### 13.9 客户端实现示例

**JavaScript (EventSource)**:

```javascript
const eventSource = new EventSource('/api/v1/ai/product-qa/chat', {
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  }
});

// POST 请求需要使用 fetch + ReadableStream
const response = await fetch('/api/v1/ai/product-qa/chat', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
  },
  body: JSON.stringify({
    question: '百万医疗险和重疾险的区别？',
    knowledge_scope: 'all'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split('\n');

  for (const line of lines) {
    if (line.startsWith('event: ')) {
      const eventType = line.slice(7);
      // 处理事件类型
    }
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      // 处理事件数据
    }
  }
}
```

---

## 附录

### A. HTTP 状态码速查

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| `200` | OK | 成功（含合规检查不通过但请求成功） |
| `201` | Created | 资源创建成功 |
| `204` | No Content | 删除成功（无响应体） |
| `400` | Bad Request | 请求格式错误 |
| `401` | Unauthorized | 未认证 / Token 过期 |
| `403` | Forbidden | 权限不足 / 账号禁用 |
| `404` | Not Found | 资源不存在 |
| `409` | Conflict | 业务冲突（重复创建等） |
| `413` | Payload Too Large | 请求体/文件过大 |
| `422` | Unprocessable Entity | 参数校验失败 |
| `429` | Too Many Requests | 频率超限 |
| `500` | Internal Server Error | 服务器内部错误 |
| `503` | Service Unavailable | 服务不可用（AI服务、数据库等） |

### B. 数据类型约定

| 类型 | 格式 | 示例 |
|------|------|------|
| ID | `前缀_随机字符` | `usr_a1b2c3d4`、`cus_001`、`conv_x1y2z3` |
| 时间 | ISO 8601 + 时区 | `2025-01-15T10:00:00+08:00` |
| 金额 | 数字（单位：元） | `6000`、`128.50` |
| 百分比 | 数字（0-100） | `85.5` |
| 枚举 | 小写下划线 | `objection_handling`、`pending_review` |

### C. 请求头汇总

| Header | 必填 | 说明 |
|--------|------|------|
| `Authorization` | ✅ | `Bearer <access_token>` |
| `Content-Type` | 视接口 | `application/json` 或 `multipart/form-data` |
| `Accept` | SSE 接口 | `text/event-stream` |
| `X-Request-ID` | ❌ | 客户端生成的请求追踪 ID，不传则服务端生成 |
| `X-Client-Version` | ❌ | 客户端版本号，用于兼容性追踪 |

---

> **文档维护说明**: 本文档由产品研发团队维护，每次 API 变更需同步更新。变更记录通过 Git 版本管理追踪。

