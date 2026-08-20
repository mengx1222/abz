# 数据库设计文档 — 安诊保 AI 副驾

> **文档状态**：当前有效 · 30 张表 / **10 个 Alembic 迁移（head=0010_audit_log_org_scope）**（与 backend/app/models 与 backend/alembic/versions 一致）
> 最后校准：2026-08-17


## 1. 设计概述

### 1.1 数据库选型

| 组件 | 技术选型 | 版本 | 用途 |
|------|---------|------|------|
| 主数据库 | PostgreSQL | 16+ | 关系型数据持久化存储 |
| 向量扩展 | pgvector | 0.7+ | 文档向量检索（RAG） |
| 缓存 | Redis | 7.0+ | 会话缓存、热数据、限流计数 |
| 迁移工具 | Alembic | — | 数据库版本管理 |

### 1.2 设计原则

1. **三范式为主**：核心业务表严格遵循第三范式，减少数据冗余与更新异常。
2. **JSONB 补充**：仅在以下场景使用 JSONB——
   - 扩展元数据（metadata），如文档附加属性、AI 分析结果等非结构化信息；
   - 标签数组（tags），轻量级多值属性；
   - 配置项（scoring_rules、keywords），结构不固定或频繁变更的集合数据。
3. **软删除**：所有表统一采用 `is_deleted + deleted_at` 字段，不执行物理删除，保留审计追溯能力。
4. **审计字段**：每张表均包含 `created_at`、`updated_at`、`created_by`、`updated_by` 四个审计字段，确保数据变更可追踪。
5. **字段级权限**：敏感字段（客户手机号、身份证号等）通过 PostgreSQL 行级安全策略（RLS）+ 应用层加密实现访问控制。
6. **完整审计链**：所有业务关键操作通过 `audit_logs` 表记录，形成完整操作链条。

### 1.3 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| 表名 | snake_case，复数形式 | `users`、`customer_tags`、`document_chunks` |
| 字段名 | snake_case | `created_at`、`intent_score` |
| 主键 | `id`，统一 UUID | — |
| 外键 | `{关联表单数}_id` | `user_id`、`organization_id` |
| 布尔字段 | `is_xxx_` 前缀 | `is_deleted`、`is_active` |
| 关联表（中间表） | `{表1}_{表2}` | `role_permissions`、`community_likes` |
| 索引 | `idx_{表名}_{字段名}` | `idx_customers_owner_id` |
| 唯一约束 | `uq_{表名}_{字段名}` | `uq_users_phone` |
| 检查约束 | `ck_{表名}_{描述}` | `ck_training_scores_score_range` |

---

## 2. 公共字段规范

所有业务表（除中间表外）均包含以下公共字段：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键，全局唯一标识 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间（带时区） |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 最后更新时间 |
| created_by | UUID | FK → users(id), NOT NULL | 创建人 |
| updated_by | UUID | FK → users(id), NOT NULL | 最后更新人 |
| is_deleted | BOOLEAN | NOT NULL, DEFAULT false | 软删除标记 |
| deleted_at | TIMESTAMPTZ | | 删除时间，NULL 表示未删除 |

**更新触发器**：所有表均启用 `ON UPDATE` 触发器，自动将 `updated_at` 设为 `now()`。

**中间表**（如 `role_permissions`、`community_likes`）仅包含 `id`、`created_at`，不含完整审计字段。

---

## 3. 数据库 ER 概览

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        安诊保 AI 副驾 — ER 关系总览                              │
└─────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐     1:N     ┌──────────────┐     1:N     ┌──────────────────┐
  │organizations│◄──────────│    users      │──────────►│   customers      │
  │  (机构)     │  parent_id │  (用户/代理人) │ owner_id │    (客户)         │
  └──────┬───┘            └──┬───┬───────┘            └──┬───┬──────────┘
         │                   │   │                       │   │
         │              ┌────┘   └───┐            ┌──────┘   └──────────┐
         │              ▼            ▼            ▼                     ▼
         │        ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌────────────────┐
         │        │  roles   │  │conversations│  │customer_tags │  │customer_inter-  │
         │        │  (角色)   │  │ (AI对话)    │  │ (客户标签)    │  │  actions(沟通)   │
         │        └────┬─────┘  └─────┬─────┘  └──────────────┘  └────────────────┘
         │             │              │                                  │
         │        ┌────┴──────┐       │ 1:N                        ┌────┴───────────┐
         │        │   role_   │       ▼                            │customer_        │
         │        │permissions│  ┌──────────┐                      │followups(跟进)   │
         │        │(角色权限)  │  │ messages  │                      └────────────────┘
         │        └────┬──────┘  │(对话消息)  │
         │             │         └──────────┘
         │        ┌────┴──────┐
         │        │permissions│
         │        │  (权限)   │
         │        └───────────┘
         │
    ┌────┴──────────────────────────────────────────────────────────┐
    │                     产品与知识域                                  │
    │                                                                │
    │  ┌──────────┐   1:N   ┌────────────────┐   1:N   ┌───────────────┐
    │  │ products  │────────►│   documents     │────────►│document_versions│
    │  │ (产品)    │         │   (知识文档)    │         │  (文档版本)     │
    │  └────┬─────┘         └───────┬────────┘         └───────────────┘
    │       │                       │
    │  ┌────┴──────────┐   ┌───────┴────────┐
    │  │product_versions│   │document_chunks  │  ← pgvector 向量检索
    │  │ (产品版本)     │   │(文档切片/向量)   │
    │  └───────────────┘   └────────────────┘
    │                       ┌───────────────────┐
    │                       │knowledge_permissions│
    │                       │ (知识权限)          │
    │                       └───────────────────┘
    └────────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────────┐
    │                     话术与陪练域                                  │
    │                                                                │
    │  ┌──────────┐   1:N   ┌─────────────────┐                      │
    │  │  scripts  │────────►│ script_versions  │                      │
    │  │  (话术)    │         │  (话术版本)      │                      │
    │  └──────────┘         └─────────────────┘                      │
    │                                                                │
    │  ┌──────────────────┐  1:N  ┌──────────────────┐               │
    │  │training_scenarios │──────►│training_sessions  │               │
    │  │  (陪练场景)       │       │  (陪练会话)       │               │
    │  └──────────────────┘       └────────┬─────────┘               │
    │                                       │ 1:N                     │
    │                              ┌────────┴─────────┐               │
    │                              │training_messages   │               │
    │                              │  (陪练消息)        │               │
    │                              └──────────────────┘               │
    │                              ┌──────────────────┐               │
    │                              │ training_scores    │               │
    │                              │  (陪练评分)        │               │
    │                              └──────────────────┘               │
    └────────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────────┐
    │                     社区与合规域                                  │
    │                                                                │
    │  ┌─────────────────┐  1:N  ┌──────────────────┐               │
    │  │ community_posts   │──────►│community_comments  │               │
    │  │  (社区帖子)       │       │  (社区评论)        │               │
    │  └─────────────────┘       └──────────────────┘               │
    │         │                                                    │
    │  ┌──────┴──────────┐                                         │
    │  │ community_likes   │                                         │
    │  │  (社区点赞)       │                                         │
    │  └─────────────────┘                                         │
    │                                                                │
    │  ┌──────────────────┐  1:N  ┌──────────────────┐               │
    │  │compliance_rules   │──────►│compliance_reviews  │               │
    │  │  (合规规则)       │       │  (合规审查)        │               │
    │  └──────────────────┘       └──────────────────┘               │
    └────────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────────┐
    │                     系统与监控域                                  │
    │                                                                │
    │  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
    │  │ ai_requests   │──1:1─►│ ai_feedback   │       │ audit_logs   │
    │  │ (AI请求监控)  │       │ (AI反馈)      │       │ (审计日志)   │
    │  └──────────────┘       └──────────────┘       └──────────────┘
    │                                                                │
    │  ┌──────────────┐       ┌──────────────┐                       │
    │  │notifications │       │system_configs│                       │
    │  │  (通知)       │       │ (系统配置)    │                       │
    │  └──────────────┘       └──────────────┘                       │
    └────────────────────────────────────────────────────────────────┘
```

---

## 4. 表结构详细设计

> **说明**：以下所有表均继承第 2 节所述公共字段，字段列表中仅列出**业务特有字段**，公共字段不再重复。

---

### 4.1 用户与权限

---

#### 4.1.1 users（用户表）

**用途说明**：存储系统所有用户信息，包括保险代理人、主管、管理员等。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| phone | VARCHAR(20) | UNIQUE, NOT NULL | 手机号（登录账号） |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希（bcrypt） |
| name | VARCHAR(100) | NOT NULL | 姓名 |
| avatar_url | VARCHAR(500) | | 头像URL |
| role_id | UUID | FK → roles(id) | 角色 |
| organization_id | UUID | FK → organizations(id) | 所属机构 |
| team_id | UUID | FK → users(id), NULLABLE | 所属团队（主管用户ID） |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态：active / disabled / locked |
| last_login_at | TIMESTAMPTZ | | 最后登录时间 |
| demo_mode | BOOLEAN | NOT NULL, DEFAULT false | 是否 Demo 用户 |
| employee_id | VARCHAR(50) | | 工号 |
| email | VARCHAR(200) | | 邮箱 |
| department | VARCHAR(100) | | 部门 |
| title | VARCHAR(100) | | 职位 |
| metadata | JSONB | DEFAULT '{}' | 扩展信息 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_users_phone | UNIQUE | phone | 手机号唯一 |
| idx_users_role_id | B-Tree | role_id | 角色查询 |
| idx_users_organization_id | B-Tree | organization_id | 机构查询 |
| idx_users_team_id | B-Tree | team_id | 团队查询 |
| idx_users_status | B-Tree | status | 状态筛选 |
| idx_users_demo_mode | B-Tree | demo_mode | Demo用户筛选 |

**关系**：
- `role_id` → `roles(id)`
- `organization_id` → `organizations(id)`
- `team_id` → `users(id)`（自引用，指向团队主管）

---

#### 4.1.2 roles（角色表）

**用途说明**：定义系统角色，支持层级化的权限管理。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| code | VARCHAR(50) | UNIQUE, NOT NULL | 角色代码：AGENT / TEAM_LEADER / BRANCH_ADMIN / HQ_ADMIN / SYSTEM_ADMIN |
| name | VARCHAR(100) | NOT NULL | 角色名称 |
| description | TEXT | | 角色描述 |
| level | INTEGER | NOT NULL, DEFAULT 0 | 权限层级（数值越大权限越高） |
| is_system | BOOLEAN | DEFAULT false | 是否系统内置角色（不可删除） |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_roles_code | UNIQUE | code | 角色代码唯一 |
| idx_roles_level | B-Tree | level | 层级排序 |

**关系**：
- 通过 `role_permissions` 中间表关联 `permissions`

---

#### 4.1.3 permissions（权限表）

**用途说明**：定义系统细粒度权限项，采用「资源 + 操作」模式。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| code | VARCHAR(100) | UNIQUE, NOT NULL | 权限代码，如 `customer:view`、`ai:chat` |
| name | VARCHAR(100) | NOT NULL | 权限名称 |
| resource | VARCHAR(50) | NOT NULL | 资源类型：customer / product / knowledge / ai / training / community / compliance / system |
| action | VARCHAR(50) | NOT NULL | 操作类型：view / create / edit / delete / export / approve |
| description | TEXT | | 权限描述 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_permissions_code | UNIQUE | code | 权限代码唯一 |
| idx_permissions_resource | B-Tree | resource | 资源类型查询 |
| idx_permissions_resource_action | B-Tree | (resource, action) | 资源+操作联合查询 |

**关系**：
- 通过 `role_permissions` 中间表关联 `roles`

---

#### 4.1.4 role_permissions（角色-权限关联表）

**用途说明**：角色与权限的多对多关联中间表。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| role_id | UUID | FK → roles(id), NOT NULL | 角色ID |
| permission_id | UUID | FK → permissions(id), NOT NULL | 权限ID |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_role_permissions_role_perm | UNIQUE | (role_id, permission_id) | 防止重复关联 |
| idx_role_permissions_role_id | B-Tree | role_id | 按角色查询 |
| idx_role_permissions_permission_id | B-Tree | permission_id | 按权限查询 |

---

#### 4.1.5 organizations（机构表）

**用途说明**：支持多级组织架构（总部 → 分公司 → 支公司 → 团队），使用自引用实现树形结构。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 机构名称 |
| code | VARCHAR(50) | UNIQUE | 机构代码 |
| type | VARCHAR(20) | NOT NULL | 层级类型：HQ / BRANCH / SUB_BRANCH / TEAM |
| parent_id | UUID | FK → organizations(id), NULLABLE | 上级机构 |
| level | INTEGER | NOT NULL, DEFAULT 0 | 层级深度（根节点为0） |
| path | VARCHAR(1000) | | 层级路径（如 `/hq/branch1/team1/`），加速树查询 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态：active / disabled |
| contact_phone | VARCHAR(20) | | 联系电话 |
| address | VARCHAR(500) | | 地址 |
| metadata | JSONB | DEFAULT '{}' | 扩展信息 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_organizations_code | UNIQUE | code | 机构代码唯一 |
| idx_organizations_parent_id | B-Tree | parent_id | 父级查询 |
| idx_organizations_type | B-Tree | type | 类型筛选 |
| idx_organizations_path | B-Tree | path | 路径查询（前缀匹配） |
| idx_organizations_level | B-Tree | level | 层级查询 |

**关系**：
- `parent_id` → `organizations(id)`（自引用）

---

### 4.2 客户管理

---

#### 4.2.1 customers（客户表）

**用途说明**：存储代理人管理的客户信息，包含客户画像、跟进阶段、意向评分等核心销售数据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| owner_id | UUID | FK → users(id), NOT NULL | 负责代理人 |
| name | VARCHAR(100) | NOT NULL | 客户姓名 |
| age | INTEGER | | 年龄 |
| gender | VARCHAR(10) | | 性别：male / female / unknown |
| phone | VARCHAR(255) | | 手机号（应用层加密存储） |
| phone_masked | VARCHAR(20) | | 脱敏手机号（如 138****5678） |
| id_card | VARCHAR(255) | | 身份证号（应用层加密存储） |
| id_card_masked | VARCHAR(20) | | 脱敏身份证号 |
| customer_type | VARCHAR(50) | | 客户类型：chronic_disease / elderly / family / standard |
| stage | VARCHAR(30) | NOT NULL, DEFAULT 'new_lead' | 销售阶段：new_lead / first_contact / need_discovery / proposal / objection_handling / closing / closed_won / closed_lost / follow_up |
| intent_score | INTEGER | DEFAULT 0 | 购买意向分 0-100 |
| price_sensitivity | VARCHAR(10) | | 价格敏感度：high / medium / low |
| service_sensitivity | VARCHAR(10) | | 服务敏感度：high / medium / low |
| tags | JSONB | DEFAULT '[]' | 标签数组，如 `['慢病客户','高意向','老年']` |
| ai_analysis | JSONB | DEFAULT '{}' | AI 分析结果（客户画像、需求洞察等） |
| next_followup_at | TIMESTAMPTZ | | 下次跟进时间 |
| last_contact_at | TIMESTAMPTZ | | 最后联系时间 |
| source | VARCHAR(50) | | 客户来源：referral / self_developed / online / event / other |
| notes | TEXT | | 备注 |
| insurance_history | JSONB | DEFAULT '[]' | 已有保险信息数组 |
| family_members | JSONB | DEFAULT '[]' | 家庭成员信息 |
| health_conditions | JSONB | DEFAULT '{}' | 健康状况 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_customers_owner_id | B-Tree | owner_id | 代理人客户列表 |
| idx_customers_stage | B-Tree | stage | 阶段筛选 |
| idx_customers_customer_type | B-Tree | customer_type | 客户类型筛选 |
| idx_customers_intent_score | B-Tree | intent_score | 意向分排序 |
| idx_customers_next_followup | B-Tree | next_followup_at | 待跟进查询 |
| idx_customers_tags | GIN | tags | JSONB 标签检索 |
| idx_customers_owner_stage | B-Tree | (owner_id, stage) | 代理人+阶段联合查询 |
| idx_customers_last_contact | B-Tree | last_contact_at | 最近联系排序 |
| idx_customers_active | PARTIAL | (owner_id) WHERE is_deleted = false | 仅活跃客户 |

**关系**：
- `owner_id` → `users(id)`

**RLS 策略**：
- 代理人仅能查看自己名下的客户
- 团队主管可查看团队成员名下的客户
- 分公司管理员可查看本分公司所有客户
- 总部管理员可查看所有客户

---

#### 4.2.2 customer_tags（客户标签表）

**用途说明**：独立的标签管理表，用于标签的标准化定义和复用，与 customers 表的 `tags` JSONB 字段配合使用。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(50) | NOT NULL | 标签名称 |
| category | VARCHAR(50) | | 标签分类：customer_type / preference / source / behavior / custom |
| color | VARCHAR(20) | | 标签颜色（前端展示用） |
| sort_order | INTEGER | DEFAULT 0 | 排序序号 |
| is_system | BOOLEAN | DEFAULT false | 是否系统预置标签 |
| organization_id | UUID | FK → organizations(id), NULLABLE | 所属机构（NULL 表示全局标签） |
| usage_count | INTEGER | DEFAULT 0 | 使用次数（冗余计数，定期同步） |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_customer_tags_name_org | UNIQUE | (name, organization_id) | 同一机构下标签名唯一 |
| idx_customer_tags_category | B-Tree | category | 分类查询 |
| idx_customer_tags_organization_id | B-Tree | organization_id | 机构标签查询 |

**关系**：
- `organization_id` → `organizations(id)`

---

#### 4.2.3 customer_interactions（客户沟通记录表）

**用途说明**：记录代理人与客户之间的每次沟通详情，包括沟通渠道、内容摘要、AI 辅助信息等。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK → customers(id), NOT NULL | 客户 |
| user_id | UUID | FK → users(id), NOT NULL | 沟通代理人 |
| type | VARCHAR(30) | NOT NULL | 沟通类型：phone / wechat / offline / video / other |
| direction | VARCHAR(10) | NOT NULL | 方向：inbound（客户来电） / outbound（代理人外呼） |
| duration_seconds | INTEGER | | 沟通时长（秒） |
| summary | TEXT | | 沟通摘要（AI 生成或手动填写） |
| content | TEXT | | 沟通详细内容 |
| key_points | JSONB | DEFAULT '[]' | 关键要点数组 |
| next_actions | JSONB | DEFAULT '[]' | 后续行动项 |
| sentiment | VARCHAR(20) | | 情绪分析：positive / neutral / negative |
| ai_suggestions | JSONB | DEFAULT '[]' | AI 给出的建议 |
| compliance_flags | JSONB | DEFAULT '[]' | 合规标记 |
| recording_url | VARCHAR(1000) | | 录音/录像URL |
| occurred_at | TIMESTAMPTZ | NOT NULL | 沟通发生时间 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_interactions_customer_id | B-Tree | customer_id | 客户沟通历史 |
| idx_interactions_user_id | B-Tree | user_id | 代理人沟通记录 |
| idx_interactions_type | B-Tree | type | 类型筛选 |
| idx_interactions_occurred_at | B-Tree | occurred_at | 时间范围查询 |
| idx_interactions_customer_occurred | B-Tree | (customer_id, occurred_at DESC) | 客户沟通时间线 |

**关系**：
- `customer_id` → `customers(id)`
- `user_id` → `users(id)`

---

#### 4.2.4 customer_followups（客户跟进计划表）

**用途说明**：管理客户跟进计划与执行情况，支持跟进提醒和完成状态追踪。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| customer_id | UUID | FK → customers(id), NOT NULL | 客户 |
| user_id | UUID | FK → users(id), NOT NULL | 负责代理人 |
| type | VARCHAR(30) | NOT NULL | 跟进类型：phone / wechat / visit / message / email |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | 状态：pending / in_progress / completed / cancelled / overdue |
| title | VARCHAR(200) | NOT NULL | 跟进主题 |
| content | TEXT | | 跟进内容/计划 |
| planned_at | TIMESTAMPTZ | NOT NULL | 计划跟进时间 |
| completed_at | TIMESTAMPTZ | | 实际完成时间 |
| result | TEXT | | 跟进结果 |
| ai_suggestion | TEXT | | AI 生成的跟进建议 |
| priority | VARCHAR(10) | DEFAULT 'medium' | 优先级：high / medium / low |
| interaction_id | UUID | FK → customer_interactions(id), NULLABLE | 关联沟通记录 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_followups_customer_id | B-Tree | customer_id | 客户跟进列表 |
| idx_followups_user_id | B-Tree | user_id | 代理人跟进任务 |
| idx_followups_status | B-Tree | status | 状态筛选 |
| idx_followups_planned_at | B-Tree | planned_at | 计划时间查询 |
| idx_followups_pending | PARTIAL | (user_id, planned_at) WHERE status = 'pending' AND is_deleted = false | 待跟进任务 |
| idx_followups_overdue | PARTIAL | (user_id) WHERE status = 'overdue' AND is_deleted = false | 逾期任务 |

**关系**：
- `customer_id` → `customers(id)`
- `user_id` → `users(id)`
- `interaction_id` → `customer_interactions(id)`

---

### 4.3 产品与知识

---

#### 4.3.1 products（保险产品表）

**用途说明**：存储保险产品基本信息，支持产品版本管理。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 产品名称 |
| code | VARCHAR(50) | UNIQUE, NOT NULL | 产品代码 |
| type | VARCHAR(50) | | 产品类型：standard / chronic_disease / elderly / family |
| category | VARCHAR(50) | | 险种类别：medical / critical_illness / accident / life |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态：active / inactive / archived |
| description | TEXT | | 产品简介 |
| features | JSONB | DEFAULT '[]' | 产品特点数组 |
| target_customers | JSONB | DEFAULT '[]' | 目标客户群体 |
| coverage_summary | JSONB | DEFAULT '{}' | 保障概要 |
| premium_range | JSONB | DEFAULT '{}' | 保费区间 |
| insurance_company | VARCHAR(200) | | 保险公司 |
| sales_guide | TEXT | | 销售指引 |
| faq | JSONB | DEFAULT '[]' | 常见问题 |
| sort_order | INTEGER | DEFAULT 0 | 排序序号 |
| thumbnail_url | VARCHAR(500) | | 产品缩略图 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_products_code | UNIQUE | code | 产品代码唯一 |
| idx_products_type | B-Tree | type | 类型筛选 |
| idx_products_category | B-Tree | category | 险种筛选 |
| idx_products_status | B-Tree | status | 状态筛选 |
| idx_products_target_customers | GIN | target_customers | 目标客户 JSONB 检索 |

**关系**：
- 被 `documents`、`product_versions` 引用

---

#### 4.3.2 product_versions（产品版本表）

**用途说明**：管理产品条款、费率的版本变更历史。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| product_id | UUID | FK → products(id), NOT NULL | 产品 |
| version | VARCHAR(20) | NOT NULL | 版本号（如 1.0、1.1、2.0） |
| changelog | TEXT | | 版本变更说明 |
| terms | JSONB | DEFAULT '{}' | 保险条款（结构化存储） |
| premium_table | JSONB | DEFAULT '{}' | 费率表 |
| effective_date | DATE | | 生效日期 |
| expiry_date | DATE, NULLABLE | | 失效日期 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft' | 状态：draft / active / expired |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_product_versions_product_version | UNIQUE | (product_id, version) | 产品+版本唯一 |
| idx_product_versions_product_id | B-Tree | product_id | 产品版本列表 |
| idx_product_versions_status | B-Tree | status | 状态筛选 |
| idx_product_versions_effective | B-Tree | effective_date | 生效日期查询 |

**关系**：
- `product_id` → `products(id)`

---

#### 4.3.3 documents（知识文档表）

**用途说明**：存储保险产品知识库文档，支持文档版本管理和 RAG 检索统计。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| product_id | UUID | FK → products(id), NULLABLE | 关联产品（NULL 表示通用知识） |
| name | VARCHAR(500) | NOT NULL | 文档名称 |
| type | VARCHAR(30) | NOT NULL | 文件格式：PDF / DOCX / PPTX / TXT / MD |
| version | VARCHAR(20) | NOT NULL | 当前版本号 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft' | 状态：draft / pending_review / published / expired |
| upload_path | VARCHAR(1000) | | 文件存储路径（S3/OSS） |
| file_size | BIGINT | | 文件大小（字节） |
| chunk_count | INTEGER | DEFAULT 0 | 切片数量 |
| recall_count | INTEGER | DEFAULT 0 | RAG 召回次数 |
| error_count | INTEGER | DEFAULT 0 | 错误反馈次数 |
| effective_date | DATE | | 生效日期 |
| expiry_date | DATE, NULLABLE | | 失效日期 |
| summary | TEXT | | 文档摘要 |
| metadata | JSONB | DEFAULT '{}' | 扩展元数据 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_documents_product_id | B-Tree | product_id | 产品文档列表 |
| idx_documents_type | B-Tree | type | 格式筛选 |
| idx_documents_status | B-Tree | status | 状态筛选 |
| idx_documents_published | PARTIAL | (id, name) WHERE status = 'published' AND is_deleted = false | 已发布文档 |
| idx_documents_effective | B-Tree | effective_date | 生效日期 |
| idx_documents_recall_count | B-Tree | recall_count DESC | 召回频次排序 |

**关系**：
- `product_id` → `products(id)`
- 被 `document_versions`、`document_chunks`、`knowledge_permissions` 引用

---

#### 4.3.4 document_versions（文档版本表）

**用途说明**：记录知识文档的版本历史，支持版本回溯与对比。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| document_id | UUID | FK → documents(id), NOT NULL | 文档 |
| version | VARCHAR(20) | NOT NULL | 版本号 |
| upload_path | VARCHAR(1000) | | 该版本文件路径 |
| file_size | BIGINT | | 文件大小 |
| changelog | TEXT | | 版本变更说明 |
| chunk_count | INTEGER | DEFAULT 0 | 该版本切片数量 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft' | 状态 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_document_versions_doc_version | UNIQUE | (document_id, version) | 文档+版本唯一 |
| idx_document_versions_document_id | B-Tree | document_id | 文档版本列表 |

**关系**：
- `document_id` → `documents(id)`

---

#### 4.3.5 document_chunks（文档切片表）

**用途说明**：存储文档经 RAG 预处理后的文本切片及其向量嵌入，是 AI 知识检索的核心数据表。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| document_id | UUID | FK → documents(id), NOT NULL | 所属文档 |
| document_version_id | UUID | FK → document_versions(id), NULLABLE | 所属文档版本 |
| content | TEXT | NOT NULL | 切片文本内容 |
| page | INTEGER, NULLABLE | | 原始文档页码 |
| section | VARCHAR(500), NULLABLE | | 章节标题 |
| chunk_index | INTEGER | NOT NULL | 切片序号（文档内排序） |
| token_count | INTEGER | | Token 数量 |
| embedding | vector(1536) | | 向量嵌入（pgvector，OpenAI text-embedding-3-small 维度） |
| metadata | JSONB | DEFAULT '{}' | 附加元数据（标题、层级等） |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_chunks_document_id | B-Tree | document_id | 文档切片列表 |
| idx_chunks_chunk_index | B-Tree | (document_id, chunk_index) | 文档内切片排序 |
| idx_chunks_embedding | HNSW / IVFFlat | embedding | **向量相似度检索索引**（详见第 6 节） |
| idx_chunks_document_version | B-Tree | document_version_id | 版本切片查询 |

**向量索引说明**：
- 切片数量 < 10,000 时使用 IVFFlat 索引（`lists = sqrt(行数)`）
- 切片数量 ≥ 10,000 时使用 HNSW 索引（`m = 16, ef_construction = 64`）
- 检索使用 `<=>`（余弦距离）运算符

**关系**：
- `document_id` → `documents(id)`
- `document_version_id` → `document_versions(id)`

---

#### 4.3.6 knowledge_permissions（知识权限表）

**用途说明**：控制不同角色/机构对知识文档的访问权限，实现知识的分级管理。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| document_id | UUID | FK → documents(id), NOT NULL | 文档 |
| role_id | UUID | FK → roles(id), NULLABLE | 角色（与 organization_id 二选一或组合） |
| organization_id | UUID | FK → organizations(id), NULLABLE | 机构 |
| permission_type | VARCHAR(20) | NOT NULL | 权限类型：view / edit / approve |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_knowledge_perms_doc_role_org | UNIQUE | (document_id, role_id, organization_id, permission_type) | 防重复 |
| idx_kp_document_id | B-Tree | document_id | 文档权限列表 |
| idx_kp_role_id | B-Tree | role_id | 角色权限查询 |
| idx_kp_organization_id | B-Tree | organization_id | 机构权限查询 |

**关系**：
- `document_id` → `documents(id)`
- `role_id` → `roles(id)`
- `organization_id` → `organizations(id)`

---

### 4.4 AI 对话与话术

---

#### 4.4.1 conversations（AI 对话表）

**用途说明**：记录用户与 AI 副驾的每次对话会话。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users(id), NOT NULL | 用户 |
| title | VARCHAR(500) | | 对话标题（AI 自动生成或用户手动设置） |
| type | VARCHAR(30) | NOT NULL | 对话类型：product_qa / script_assist / customer_analysis / general |
| customer_id | UUID | FK → customers(id), NULLABLE | 关联客户 |
| product_id | UUID | FK → products(id), NULLABLE | 关联产品 |
| context | JSONB | DEFAULT '{}' | 对话上下文（传入的背景信息） |
| message_count | INTEGER | DEFAULT 0 | 消息数量（冗余计数） |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态：active / archived / deleted |
| started_at | TIMESTAMPTZ | | 开始时间 |
| last_message_at | TIMESTAMPTZ | | 最后消息时间 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_conversations_user_id | B-Tree | user_id | 用户对话列表 |
| idx_conversations_type | B-Tree | type | 类型筛选 |
| idx_conversations_customer_id | B-Tree | customer_id | 客户相关对话 |
| idx_conversations_status | B-Tree | status | 状态筛选 |
| idx_conversations_last_message | B-Tree | (user_id, last_message_at DESC) | 最近对话排序 |

**关系**：
- `user_id` → `users(id)`
- `customer_id` → `customers(id)`
- `product_id` → `products(id)`
- 被 `messages` 引用

---

#### 4.4.2 messages（对话消息表）

**用途说明**：存储对话中的每条消息，包含用户消息和 AI 回复。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| conversation_id | UUID | FK → conversations(id), NOT NULL | 对话 |
| role | VARCHAR(20) | NOT NULL | 发送者：user / assistant / system |
| content | TEXT | NOT NULL | 消息内容 |
| content_type | VARCHAR(20) | DEFAULT 'text' | 内容类型：text / markdown / json |
| token_count | INTEGER | | Token 数量 |
| model | VARCHAR(100) | | 使用的 AI 模型（仅 assistant 消息） |
| knowledge_sources | JSONB | DEFAULT '[]' | RAG 检索来源（文档ID+切片ID+相关性分数） |
| compliance_check | JSONB | DEFAULT '{}' | 合规检查结果 |
| feedback | VARCHAR(20) | | 用户反馈：helpful / unhelpful / NULL |
| feedback_comment | TEXT | | 反馈说明 |
| latency_ms | INTEGER | | 响应耗时（仅 assistant 消息） |
| metadata | JSONB | DEFAULT '{}' | 扩展信息 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_messages_conversation_id | B-Tree | conversation_id | 对话消息列表 |
| idx_messages_role | B-Tree | role | 角色筛选 |
| idx_messages_feedback | B-Tree | feedback | 反馈筛选 |
| idx_messages_conversation_order | B-Tree | (conversation_id, created_at ASC) | 消息时间排序 |

**关系**：
- `conversation_id` → `conversations(id)`

---

#### 4.4.3 scripts（话术模板表）

**用途说明**：存储销售话术模板，支持版本管理和分类检索。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| title | VARCHAR(500) | NOT NULL | 话术标题 |
| category | VARCHAR(50) | NOT NULL | 分类：opening / need_discovery / product_intro / objection_handling / closing / follow_up |
| scenario | VARCHAR(100) | | 适用场景 |
| product_id | UUID | FK → products(id), NULLABLE | 关联产品 |
| customer_type | VARCHAR(50) | | 适用客户类型 |
| current_version | VARCHAR(20) | NOT NULL | 当前版本号 |
| content | TEXT | NOT NULL | 话术内容（当前版本） |
| key_points | JSONB | DEFAULT '[]' | 关键要点 |
| tips | JSONB | DEFAULT '[]' | 话术技巧 |
| usage_count | INTEGER | DEFAULT 0 | 使用次数 |
| like_count | INTEGER | DEFAULT 0 | 点赞数 |
| source | VARCHAR(20) | DEFAULT 'ai' | 来源：ai / user / system |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态：active / archived |
| tags | JSONB | DEFAULT '[]' | 标签 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_scripts_category | B-Tree | category | 分类查询 |
| idx_scripts_scenario | B-Tree | scenario | 场景查询 |
| idx_scripts_product_id | B-Tree | product_id | 产品话术 |
| idx_scripts_customer_type | B-Tree | customer_type | 客户类型话术 |
| idx_scripts_status | B-Tree | status | 状态筛选 |
| idx_scripts_tags | GIN | tags | 标签检索 |
| idx_scripts_usage_count | B-Tree | usage_count DESC | 热门话术 |
| idx_scripts_source | B-Tree | source | 来源筛选 |

**关系**：
- `product_id` → `products(id)`
- 被 `script_versions` 引用

---

#### 4.4.4 script_versions（话术版本表）

**用途说明**：记录话术的版本历史，支持对比和回溯。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| script_id | UUID | FK → scripts(id), NOT NULL | 话术 |
| version | VARCHAR(20) | NOT NULL | 版本号 |
| content | TEXT | NOT NULL | 该版本话术内容 |
| changelog | TEXT | | 版本变更说明 |
| change_type | VARCHAR(20) | | 变更类型：created / modified / regenerated |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_script_versions_script_version | UNIQUE | (script_id, version) | 话术+版本唯一 |
| idx_script_versions_script_id | B-Tree | script_id | 话术版本列表 |

**关系**：
- `script_id` → `scripts(id)`

---

### 4.5 AI 陪练

---

#### 4.5.1 training_scenarios（陪练场景表）

**用途说明**：定义 AI 陪练的各种销售场景，包括客户人设、评分规则等。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 场景名称 |
| description | TEXT | | 场景描述 |
| type | VARCHAR(50) | NOT NULL | 场景类型：price_objection / need_objection / decision_objection / trust_objection / competitor_objection / chronic_disease / elderly_care / family_plan / cross_sell / general |
| difficulty | VARCHAR(20) | NOT NULL, DEFAULT 'medium' | 难度：easy / medium / hard |
| persona_prompt | TEXT | NOT NULL | AI 客户人格 Prompt（定义客户性格、背景、诉求） |
| scoring_rules | JSONB | DEFAULT '{}' | 评分规则（维度、权重、评分标准） |
| product_id | UUID | FK → products(id), NULLABLE | 关联产品 |
| customer_profile | JSONB | DEFAULT '{}' | 客户画像模板 |
| conversation_guide | JSONB | DEFAULT '[]' | 对话引导要点 |
| max_turns | INTEGER | DEFAULT 20 | 最大对话轮次 |
| time_limit_minutes | INTEGER | DEFAULT 10 | 时间限制 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| usage_count | INTEGER | DEFAULT 0 | 累计使用次数 |
| avg_score | DECIMAL(5,2) | | 平均得分 |
| completion_rate | DECIMAL(5,2) | | 完成率 |
| sort_order | INTEGER | DEFAULT 0 | 排序序号 |
| thumbnail_url | VARCHAR(500) | | 场景缩略图 |
| tags | JSONB | DEFAULT '[]' | 标签 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_training_scenarios_type | B-Tree | type | 类型筛选 |
| idx_training_scenarios_difficulty | B-Tree | difficulty | 难度筛选 |
| idx_training_scenarios_is_active | PARTIAL | (id, name, difficulty) WHERE is_active = true AND is_deleted = false | 可用场景 |
| idx_training_scenarios_product_id | B-Tree | product_id | 产品相关场景 |
| idx_training_scenarios_tags | GIN | tags | 标签检索 |
| idx_training_scenarios_usage_count | B-Tree | usage_count DESC | 热门场景 |

**关系**：
- `product_id` → `products(id)`
- 被 `training_sessions` 引用

---

#### 4.5.2 training_sessions（陪练会话表）

**用途说明**：记录每次陪练练习的会话信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users(id), NOT NULL | 练习用户（代理人） |
| scenario_id | UUID | FK → training_scenarios(id), NOT NULL | 陪练场景 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'in_progress' | 状态：in_progress / completed / abandoned / timed_out |
| started_at | TIMESTAMPTZ | NOT NULL | 开始时间 |
| ended_at | TIMESTAMPTZ | | 结束时间 |
| duration_seconds | INTEGER | | 练习时长 |
| message_count | INTEGER | DEFAULT 0 | 消息轮次 |
| final_score | DECIMAL(5,2) | | 最终得分 |
| score_detail | JSONB | DEFAULT '{}' | 评分详情 |
| ai_summary | TEXT | | AI 评语总结 |
| strengths | JSONB | DEFAULT '[]' | 优点 |
| weaknesses | JSONB | DEFAULT '[]' | 待改进点 |
| suggestions | JSONB | DEFAULT '[]' | 改进建议 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_training_sessions_user_id | B-Tree | user_id | 用户陪练记录 |
| idx_training_sessions_scenario_id | B-Tree | scenario_id | 场景练习记录 |
| idx_training_sessions_status | B-Tree | status | 状态筛选 |
| idx_training_sessions_started_at | B-Tree | started_at | 时间查询 |
| idx_training_sessions_user_score | B-Tree | (user_id, final_score DESC) | 用户成绩排名 |

**关系**：
- `user_id` → `users(id)`
- `scenario_id` → `training_scenarios(id)`
- 被 `training_messages`、`training_scores` 引用

---

#### 4.5.3 training_messages（陪练消息表）

**用途说明**：存储陪练过程中代理人与 AI 客户的每条对话消息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| session_id | UUID | FK → training_sessions(id), NOT NULL | 陪练会话 |
| role | VARCHAR(20) | NOT NULL | 角色：agent（代理人） / customer（AI客户） / system（系统提示） |
| content | TEXT | NOT NULL | 消息内容 |
| turn_number | INTEGER | NOT NULL | 轮次号 |
| token_count | INTEGER | | Token 数量 |
| latency_ms | INTEGER | | AI 响应耗时 |
| metadata | JSONB | DEFAULT '{}' | 扩展信息 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_training_messages_session_id | B-Tree | session_id | 会话消息列表 |
| idx_training_messages_session_turn | B-Tree | (session_id, turn_number ASC) | 会话内消息排序 |

**关系**：
- `session_id` → `training_sessions(id)`

---

#### 4.5.4 training_scores（陪练评分表）

**用途说明**：存储陪练结束后的多维度评分结果（JSON 结构化输出）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| session_id | UUID | FK → training_sessions(id), NOT NULL, UNIQUE | 陪练会话（一对一） |
| total_score | DECIMAL(5,2) | NOT NULL | 总分 |
| dimension_scores | JSONB | NOT NULL | 各维度得分，如：
| | | | ```json
| | | | {
| | | |   "professionalism": {"score": 85, "weight": 0.3, "comment": "..."},
| | | |   "empathy": {"score": 90, "weight": 0.2, "comment": "..."},
| | | |   "product_knowledge": {"score": 78, "weight": 0.2, "comment": "..."},
| | | |   "objection_handling": {"score": 82, "weight": 0.2, "comment": "..."},
| | | |   "closing_technique": {"score": 70, "weight": 0.1, "comment": "..."}
| | | | }
| | | | ``` |
| overall_comment | TEXT | | 综合评语 |
| strengths | JSONB | DEFAULT '[]' | 亮点列表 |
| improvements | JSONB | DEFAULT '[]' | 改进建议列表 |
| model | VARCHAR(100) | | 评分使用的模型 |
| prompt_version | VARCHAR(50) | | 评分 Prompt 版本 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_training_scores_session_id | UNIQUE | session_id | 每个会话仅一次评分 |
| idx_training_scores_total_score | B-Tree | total_score DESC | 成绩排名 |

**关系**：
- `session_id` → `training_sessions(id)`

---

### 4.6 社区

---

#### 4.6.1 community_posts（社区帖子表）

**用途说明**：存储社区内容，代理人可分享销售经验、话术心得、成功案例等。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users(id), NOT NULL | 作者 |
| title | VARCHAR(500) | NOT NULL | 标题 |
| content | TEXT | NOT NULL | 正文内容 |
| type | VARCHAR(30) | NOT NULL, DEFAULT 'experience' | 类型：experience / script / case / question / tip / celebration |
| category | VARCHAR(50) | | 分类 |
| tags | JSONB | DEFAULT '[]' | 标签 |
| view_count | INTEGER | DEFAULT 0 | 浏览量 |
| like_count | INTEGER | DEFAULT 0 | 点赞数 |
| comment_count | INTEGER | DEFAULT 0 | 评论数 |
| is_pinned | BOOLEAN | DEFAULT false | 是否置顶 |
| is_featured | BOOLEAN | DEFAULT false | 是否精选 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'published' | 状态：draft / pending_review / published / rejected / hidden |
| published_at | TIMESTAMPTZ | | 发布时间 |
| rejected_reason | TEXT | | 驳回原因 |
| images | JSONB | DEFAULT '[]' | 图片URL数组 |
| attachments | JSONB | DEFAULT '[]' | 附件信息数组 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_community_posts_user_id | B-Tree | user_id | 用户帖子 |
| idx_community_posts_type | B-Tree | type | 类型筛选 |
| idx_community_posts_status | B-Tree | status | 状态筛选 |
| idx_community_posts_tags | GIN | tags | 标签检索 |
| idx_community_posts_published | B-Tree | (published_at DESC) WHERE status = 'published' AND is_deleted = false | 最新帖子 |
| idx_community_posts_like_count | B-Tree | like_count DESC | 热门帖子 |
| idx_community_posts_pinned | PARTIAL | (id) WHERE is_pinned = true AND is_deleted = false | 置顶帖子 |

**关系**：
- `user_id` → `users(id)`
- 被 `community_comments`、`community_likes` 引用

---

#### 4.6.2 community_comments（社区评论表）

**用途说明**：存储帖子下的评论与回复，支持两级评论（评论 + 回复）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| post_id | UUID | FK → community_posts(id), NOT NULL | 帖子 |
| user_id | UUID | FK → users(id), NOT NULL | 评论者 |
| parent_id | UUID | FK → community_comments(id), NULLABLE | 父评论（NULL 为顶级评论） |
| content | TEXT | NOT NULL | 评论内容 |
| like_count | INTEGER | DEFAULT 0 | 点赞数 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'published' | 状态：published / hidden |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_community_comments_post_id | B-Tree | post_id | 帖子评论 |
| idx_community_comments_user_id | B-Tree | user_id | 用户评论 |
| idx_community_comments_parent_id | B-Tree | parent_id | 回复查询 |
| idx_community_comments_post_created | B-Tree | (post_id, created_at ASC) | 帖子评论时间排序 |

**关系**：
- `post_id` → `community_posts(id)`
- `user_id` → `users(id)`
- `parent_id` → `community_comments(id)`（自引用）

---

#### 4.6.3 community_likes（社区点赞表）

**用途说明**：记录用户对帖子和评论的点赞行为，确保一个用户只能点赞一次。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users(id), NOT NULL | 点赞用户 |
| target_id | UUID | NOT NULL | 目标ID（帖子或评论ID） |
| target_type | VARCHAR(20) | NOT NULL | 目标类型：post / comment |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 点赞时间 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_community_likes_user_target | UNIQUE | (user_id, target_id, target_type) | 防止重复点赞 |
| idx_community_likes_user_id | B-Tree | user_id | 用户点赞记录 |
| idx_community_likes_target | B-Tree | (target_type, target_id) | 按目标查询点赞数 |

**关系**：
- `user_id` → `users(id)`
- `target_id` 逻辑关联 `community_posts(id)` 或 `community_comments(id)`

---

### 4.7 合规

---

#### 4.7.1 compliance_rules（合规规则表）

**用途说明**：定义保险销售合规检查规则，支持关键词匹配和正则表达式模式匹配。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 规则名称 |
| type | VARCHAR(50) | NOT NULL | 违规类型：
| | | | - `return_promise` — 收益承诺
| | | | - `absolute_expression` — 绝对化表达
| | | | - `false_comparison` — 虚假比较
| | | | - `exaggerated_coverage` — 夸大保障
| | | | - `improper_underwriting` — 不当核保结论
| | | | - `improper_claim` — 不当理赔承诺
| | | | - `misleading_sales` — 误导销售
| | | | - `sensitive_medical` — 敏感医疗结论 |
| keywords | JSONB | DEFAULT '[]' | 关键词列表，如 `['保证收益', '稳赚不赔', '零风险']` |
| patterns | JSONB | DEFAULT '[]' | 正则表达式列表 |
| description | TEXT | | 规则说明 |
| severity | VARCHAR(10) | NOT NULL | 严重程度：HIGH / MEDIUM / LOW |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| violation_count | INTEGER | DEFAULT 0 | 触发次数 |
| sort_order | INTEGER | DEFAULT 0 | 排序 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_compliance_rules_type | B-Tree | type | 类型查询 |
| idx_compliance_rules_severity | B-Tree | severity | 严重程度 |
| idx_compliance_rules_active | PARTIAL | (id) WHERE is_active = true AND is_deleted = false | 活跃规则 |

---

#### 4.7.2 compliance_reviews（合规审查记录表）

**用途说明**：记录每次合规检查的详细结果，包括触发规则、原文位置、处置建议等。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| rule_id | UUID | FK → compliance_rules(id), NOT NULL | 触发的规则 |
| user_id | UUID | FK → users(id), NOT NULL | 被检查用户 |
| source_type | VARCHAR(30) | NOT NULL | 来源类型：message / script / community_post |
| source_id | UUID | NOT NULL | 来源记录ID |
| content | TEXT | NOT NULL | 触发违规的原文内容 |
| matched_keyword | VARCHAR(200), NULLABLE | 匹配到的关键词 |
| matched_pattern | VARCHAR(500), NULLABLE | 匹配到的正则表达式 |
| context | TEXT | | 上下文（违规内容前后文） |
| severity | VARCHAR(10) | NOT NULL | 严重程度 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | 处置状态：pending / confirmed / dismissed / escalated |
| reviewed_by | UUID | FK → users(id), NULLABLE | 审核人 |
| reviewed_at | TIMESTAMPTZ | | 审核时间 |
| review_comment | TEXT | | 审核意见 |
| suggestion | TEXT | | AI 给出的修正建议 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_compliance_reviews_rule_id | B-Tree | rule_id | 规则触发记录 |
| idx_compliance_reviews_user_id | B-Tree | user_id | 用户违规记录 |
| idx_compliance_reviews_source | B-Tree | (source_type, source_id) | 按来源查询 |
| idx_compliance_reviews_status | B-Tree | status | 状态筛选 |
| idx_compliance_reviews_severity | B-Tree | severity | 严重程度 |
| idx_compliance_reviews_created_at | B-Tree | created_at DESC | 时间排序 |
| idx_compliance_reviews_pending | PARTIAL | (id) WHERE status = 'pending' AND is_deleted = false | 待审核记录 |

**关系**：
- `rule_id` → `compliance_rules(id)`
- `user_id` → `users(id)`（被检查用户）
- `reviewed_by` → `users(id)`（审核人）

---

### 4.8 AI 监控

---

#### 4.8.1 ai_requests（AI 请求监控表）

**用途说明**：记录所有 AI 请求的详细日志，用于成本监控、质量分析和问题排查。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| request_id | VARCHAR(100) | UNIQUE, NOT NULL | 请求追踪ID（全局唯一，用于链路追踪） |
| user_id | UUID | FK → users(id), NOT NULL | 发起请求的用户 |
| type | VARCHAR(30) | NOT NULL | 请求类型：
| | | | - `product_qa` — 产品知识问答
| | | | - `script_gen` — 话术生成
| | | | - `customer_analysis` — 客户分析
| | | | - `training` — 陪练
| | | | - `summarization` — 内容摘要
| | | | - `compliance_check` — 合规检查
| | | | - `score_evaluation` — 评分 |
| model | VARCHAR(100) | | 使用的 AI 模型名称 |
| provider | VARCHAR(50) | | 模型供应商：deepseek / qwen / openai / mock |
| prompt_version | VARCHAR(50) | | Prompt 模板版本 |
| input_tokens | INTEGER | | 输入 Token 数 |
| output_tokens | INTEGER | | 输出 Token 数 |
| total_tokens | INTEGER | | 总 Token 数 |
| latency_ms | INTEGER | | 请求耗时（毫秒） |
| ttfb_ms | INTEGER | | 首字节时间（毫秒） |
| status | VARCHAR(20) | NOT NULL | 状态：success / failed / timeout / rate_limited |
| error_message | TEXT | | 错误信息 |
| knowledge_sources | JSONB | DEFAULT '[]' | RAG 检索来源（文档ID、切片ID、相关性分数） |
| cost_cny | DECIMAL(10,6) | | 估算费用（人民币） |
| risk_level | VARCHAR(10), NULLABLE | | 风险等级：high / medium / low |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_ai_requests_request_id | UNIQUE | request_id | 请求追踪ID唯一 |
| idx_ai_requests_user_id | B-Tree | user_id | 用户请求记录 |
| idx_ai_requests_type | B-Tree | type | 类型查询 |
| idx_ai_requests_model | B-Tree | model | 模型查询 |
| idx_ai_requests_provider | B-Tree | provider | 供应商查询 |
| idx_ai_requests_status | B-Tree | status | 状态筛选 |
| idx_ai_requests_created_at | B-Tree | created_at DESC | 时间查询 |
| idx_ai_requests_latency | B-Tree | latency_ms | 性能分析 |
| idx_ai_requests_tokens | B-Tree | total_tokens | Token用量 |
| idx_ai_requests_cost | B-Tree | cost_cny | 费用分析 |
| idx_ai_requests_risk_level | B-Tree | risk_level | 风险查询 |

**关系**：
- `user_id` → `users(id)`
- 被 `ai_feedback` 引用

---

#### 4.8.2 ai_feedback（AI 反馈表）

**用途说明**：收集用户对 AI 回复的质量反馈，用于持续优化模型和 Prompt。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| request_id | UUID | FK → ai_requests(id), NULLABLE | 关联AI请求 |
| user_id | UUID | FK → users(id), NOT NULL | 反馈用户 |
| source_type | VARCHAR(30) | NOT NULL | 反馈来源：chat_message / training_score / script / community |
| source_id | UUID | | 来源记录ID |
| rating | INTEGER | | 评分 1-5（NULL 表示仅文字反馈） |
| feedback_type | VARCHAR(20) | NOT NULL | 反馈类型：helpful / unhelpful / inaccurate / inappropriate / other |
| comment | TEXT | | 反馈文字 |
| is_resolved | BOOLEAN | DEFAULT false | 是否已处理 |
| resolved_by | UUID | FK → users(id), NULLABLE | 处理人 |
| resolved_at | TIMESTAMPTZ | | 处理时间 |
| resolution | TEXT | | 处理说明 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_ai_feedback_request_id | B-Tree | request_id | 按请求查询 |
| idx_ai_feedback_user_id | B-Tree | user_id | 用户反馈 |
| idx_ai_feedback_source | B-Tree | (source_type, source_id) | 按来源查询 |
| idx_ai_feedback_type | B-Tree | feedback_type | 反馈类型 |
| idx_ai_feedback_rating | B-Tree | rating | 评分查询 |
| idx_ai_feedback_unresolved | PARTIAL | (id) WHERE is_resolved = false AND is_deleted = false | 待处理反馈 |

**关系**：
- `request_id` → `ai_requests(id)`
- `user_id` → `users(id)`
- `resolved_by` → `users(id)`

---

### 4.9 系统管理

---

#### 4.9.1 notifications（通知表）

**用途说明**：系统通知与消息中心，支持多种通知类型和状态管理。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users(id), NOT NULL | 接收用户 |
| type | VARCHAR(30) | NOT NULL | 通知类型：
| | | | - `followup_reminder` — 跟进提醒
| | | | - `compliance_alert` — 合规预警
| | | | - `system` — 系统通知
| | | | - `community_reply` — 社区回复
| | | | - `community_like` — 社区点赞
| | | | - `training_complete` — 陪练完成
| | | | - `achievement` — 成就解锁 |
| title | VARCHAR(200) | NOT NULL | 通知标题 |
| content | TEXT | NOT NULL | 通知内容 |
| data | JSONB | DEFAULT '{}' | 附加数据（跳转链接等） |
| is_read | BOOLEAN | DEFAULT false | 是否已读 |
| read_at | TIMESTAMPTZ | | 阅读时间 |
| channel | VARCHAR(20) | DEFAULT 'in_app' | 渠道：in_app / sms / email / wechat |
| expires_at | TIMESTAMPTZ, NULLABLE | | 过期时间 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_notifications_user_id | B-Tree | user_id | 用户通知列表 |
| idx_notifications_type | B-Tree | type | 类型筛选 |
| idx_notifications_is_read | B-Tree | is_read | 已读/未读筛选 |
| idx_notifications_unread | PARTIAL | (id, created_at DESC) WHERE is_read = false AND is_deleted = false | 未读通知 |
| idx_notifications_user_created | B-Tree | (user_id, created_at DESC) | 用户通知时间排序 |
| idx_notifications_expires | B-Tree | expires_at | 过期清理 |

**关系**：
- `user_id` → `users(id)`

---

#### 4.9.2 audit_logs（审计日志表）

**用途说明**：记录系统中所有关键业务操作，形成完整审计链，满足监管合规要求。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users(id), NOT NULL | 操作人 |
| action | VARCHAR(100) | NOT NULL | 操作类型，如 `customer.create`、`script.approve`、`user.login` |
| resource_type | VARCHAR(50) | | 资源类型：customer / product / document / script / user / role / system |
| resource_id | UUID, NULLABLE | | 资源ID |
| resource_name | VARCHAR(500) | | 资源名称（冗余，便于查询展示） |
| detail | JSONB | DEFAULT '{}' | 操作详情（变更前后的 diff、请求参数等） |
| ip_address | VARCHAR(45) | | IP 地址（兼容 IPv6） |
| user_agent | VARCHAR(500) | | 用户代理（浏览器信息） |
| request_id | VARCHAR(100) | | 关联请求ID（链路追踪） |
| session_id | VARCHAR(100) | | 会话ID |
| duration_ms | INTEGER | | 操作耗时 |
| status | VARCHAR(20) | | 操作结果：success / failed |
| error_message | TEXT | | 错误信息 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| idx_audit_logs_user_id | B-Tree | user_id | 用户操作记录 |
| idx_audit_logs_action | B-Tree | action | 操作类型 |
| idx_audit_logs_resource | B-Tree | (resource_type, resource_id) | 资源操作记录 |
| idx_audit_logs_created_at | B-Tree | created_at DESC | 时间查询 |
| idx_audit_logs_request_id | B-Tree | request_id | 链路追踪 |
| idx_audit_logs_ip | B-Tree | ip_address | IP查询 |
| idx_audit_logs_detail | GIN | detail | JSONB 详情检索 |

**关系**：
- `user_id` → `users(id)`

**注意**：审计日志表仅做软删除归档，不做物理删除。建议按月分区或定期归档到冷存储。

---

#### 4.9.3 system_configs（系统配置表）

**用途说明**：存储系统级配置参数，支持动态配置更新，无需重启服务。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| key | VARCHAR(100) | UNIQUE, NOT NULL | 配置键 |
| value | TEXT | NOT NULL | 配置值 |
| value_type | VARCHAR(20) | DEFAULT 'string' | 值类型：string / integer / boolean / json |
| group | VARCHAR(50) | | 配置分组：ai / system / business / feature_flag |
| description | TEXT | | 配置说明 |
| is_public | BOOLEAN | DEFAULT false | 是否对前端公开 |
| sort_order | INTEGER | DEFAULT 0 | 排序 |

**索引设计**：

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| uq_system_configs_key | UNIQUE | key | 配置键唯一 |
| idx_system_configs_group | B-Tree | group | 分组查询 |
| idx_system_configs_public | PARTIAL | (key, value) WHERE is_public = true AND is_deleted = false | 前端可读配置 |

**预置配置示例**：

| key | value | group | 说明 |
|-----|-------|-------|------|
| ai.default_model | deepseek-chat | ai | 默认AI模型 |
| ai.max_tokens | 4096 | ai | 最大输出Token |
| ai.temperature | 0.7 | ai | 默认温度 |
| ai.rag.top_k | 5 | ai | RAG检索TopK |
| ai.rag.similarity_threshold | 0.75 | ai | 相似度阈值 |
| system.maintenance_mode | false | system | 维护模式 |
| system.max_upload_size_mb | 50 | system | 最大上传文件大小 |
| business.followup_reminder_hours | 24 | business | 跟进提醒提前时间 |
| feature.compliance_check | true | feature_flag | 合规检查功能开关 |
| feature.community | true | feature_flag | 社区功能开关 |

---

## 5. Redis 缓存设计

### 5.1 缓存 Key 命名规范

```
{业务域}:{实体}:{标识}:{字段}    例：user:session:abc123:token
ttl 统一使用秒为单位，通过 EXPIRE 命令设置
```

### 5.2 缓存用途详解

#### 5.2.1 用户 Session 缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `user:session:{session_id}` | Hash | 24h | 用户会话信息（user_id, role, org 等） |
| `user:token:{token}` | String | 24h | Token → Session ID 映射 |
| `user:permissions:{user_id}` | Set | 1h | 用户权限代码集合 |
| `user:online:{user_id}` | String | 5min | 在线心跳（定期续期） |

#### 5.2.2 AI 对话临时缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `ai:conversation:{conversation_id}:context` | Hash | 2h | 对话上下文（系统Prompt、摘要） |
| `ai:conversation:{conversation_id}:stream` | String | 10min | SSE 流式响应临时缓冲 |
| `ai:rate_limit:{user_id}` | String | 1min | 用户AI调用频率限制计数 |

#### 5.2.3 热门知识缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `knowledge:hot:{document_id}` | Hash | 6h | 热门文档摘要及元数据 |
| `knowledge:search:{query_hash}` | List | 30min | 相同查询的 RAG 结果缓存 |
| `knowledge:stats:recall` | String | 1h | 文档召回频次统计 |
| `product:detail:{product_id}` | Hash | 6h | 产品详情缓存 |

#### 5.2.4 Rate Limit 计数器

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `ratelimit:api:{user_id}:{endpoint}` | String | 1min | API 调用频率限制 |
| `ratelimit:ai:{user_id}` | String | 1min | AI 调用频率限制（每分钟N次） |
| `ratelimit:ai:daily:{user_id}` | String | 24h | AI 每日调用限额 |
| `ratelimit:login:{ip}` | String | 15min | 登录尝试频率限制 |

#### 5.2.5 Demo 数据缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `demo:user:{user_id}:initialized` | String | 永久 | Demo 用户数据初始化标记 |
| `demo:preloaded:{type}` | Hash | 永久 | 预加载的 Demo 数据引用 |
| `demo:stats:{user_id}` | Hash | 1h | Demo 仪表盘统计数据 |

#### 5.2.6 其他缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `system:config:{group}` | Hash | 10min | 系统配置缓存 |
| `notification:unread_count:{user_id}` | String | 5min | 未读通知数 |
| `community:trending` | List | 1h | 社区热门内容 |
| `training:ranking:{scenario_id}` | ZSet | 1h | 陪练排行榜 |

### 5.3 缓存更新策略

- **Cache Aside**：读时先查缓存，miss 后查 DB 并写入缓存；写时先更新 DB 再删除缓存
- **Write Through**：对高频更新的配置类数据使用
- **Cache Invalidation**：数据变更时通过事件机制主动清除相关缓存
- **TTL 兜底**：所有缓存设置 TTL，防止脏数据长期存在

---

## 6. 索引策略

### 6.1 主键索引

所有表的主键 `id`（UUID）自动创建 B-Tree 索引，由 PostgreSQL 主键约束隐式创建。

### 6.2 外键索引

所有外键字段均创建 B-Tree 索引，加速 JOIN 查询和级联操作：

```sql
-- 外键索引命名规范
CREATE INDEX idx_{表名}_{外键字段} ON {表名}({外键字段});
```

### 6.3 常用查询索引

根据业务查询模式设计复合索引和条件索引：

| 索引策略 | 适用场景 | 示例 |
|----------|---------|------|
| 单列 B-Tree | 状态筛选、类型筛选 | `idx_customers_stage` |
| 复合 B-Tree | 多条件联合查询 | `idx_customers_owner_stage` ON (owner_id, stage) |
| 排序索引 | 列表排序 | `idx_conversations_last_message` ON (user_id, last_message_at DESC) |
| 部分索引 | 带状态过滤的查询 | `WHERE status = 'active' AND is_deleted = false` |
| GIN 索引 | JSONB 内部字段检索 | `idx_customers_tags` ON tags USING GIN |

### 6.4 pgvector 向量索引

**向量字段**：`document_chunks.embedding`（vector(1536)）

```sql
-- 方案一：IVFFlat（适用于 < 10,000 条切片）
CREATE INDEX idx_chunks_embedding_ivfflat
ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- lists ≈ sqrt(总行数)

-- 方案二：HNSW（适用于 ≥ 10,000 条切片，推荐）
CREATE INDEX idx_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**查询方式**：

```sql
-- 余弦相似度检索（距离越小越相似）
SELECT dc.id, dc.content, dc.document_id,
       1 - (dc.embedding <=> $1::vector) AS similarity
FROM document_chunks dc
WHERE dc.is_deleted = false
ORDER BY dc.embedding <=> $1::vector
LIMIT 5;
```

**索引选择建议**：
- 数据量 < 1 万：IVFFlat，构建快，查询精度高
- 数据量 1~50 万：HNSW（m=16, ef_construction=64），查询速度快
- 数据量 > 50 万：HNSW（m=32, ef_construction=100），增加精度

### 6.5 部分索引策略

针对高频查询中的状态过滤条件，使用部分索引减少索引大小、提升查询性能：

```sql
-- 仅索引活跃客户
CREATE INDEX idx_customers_active
ON customers(owner_id)
WHERE is_deleted = false;

-- 仅索引待跟进任务
CREATE INDEX idx_followups_pending
ON customer_followups(user_id, planned_at)
WHERE status = 'pending' AND is_deleted = false;

-- 仅索引未读通知
CREATE INDEX idx_notifications_unread
ON notifications(user_id, created_at DESC)
WHERE is_read = false AND is_deleted = false;

-- 仅索引活跃合规规则
CREATE INDEX idx_compliance_rules_active
ON compliance_rules(id)
WHERE is_active = true AND is_deleted = false;
```

### 6.6 索引维护

- **定期 VACUUM**：每周执行 `VACUUM ANALYZE`，更新统计信息
- **REINDEX**：每月对碎片化严重的索引执行 `REINDEX CONCURRENTLY`
- **监控**：通过 `pg_stat_user_indexes` 监控索引使用率，移除无用索引

---

## 7. 数据安全

### 7.1 字段级加密

对客户敏感信息在应用层进行 AES-256-GCM 加密后存储：

| 表 | 字段 | 加密方式 | 说明 |
|----|------|---------|------|
| customers | phone | AES-256-GCM | 手机号加密，密文存储于 `phone` 字段 |
| customers | id_card | AES-256-GCM | 身份证号加密 |
| customer_interactions | content | AES-256-GCM（可选） | 沟通详细内容加密 |
| users | password_hash | bcrypt | 密码哈希（单向，非加密） |

**加密实现要点**：
- 密钥通过 KMS（密钥管理服务）管理，不硬编码
- 每条记录使用唯一 IV（初始化向量）
- 加密后的密文以 Base64 编码存储
- 脱敏值（`phone_masked`、`id_card_masked`）单独存储，查询展示时无需解密

### 7.2 脱敏策略

| 数据类型 | 脱敏规则 | 示例 |
|---------|---------|------|
| 手机号 | 中间4位替换为 `****` | 138****5678 |
| 身份证号 | 保留前3后4位 | 110***********1234 |
| 姓名 | 保留姓氏，名替换为 `*` | 张** |
| 银行卡号 | 保留后4位 | ************5678 |
| 地址 | 保留省市，详细地址替换 | 北京市朝阳区*** |

**脱敏时机**：
- **存储时**：写入 `phone_masked`、`id_card_masked` 字段
- **传输时**：API 响应中对敏感字段进行脱敏
- **展示时**：前端根据用户权限展示原值或脱敏值

### 7.3 行级安全策略（RLS）

PostgreSQL 原生 RLS 策略，实现数据隔离：

```sql
-- 启用 RLS
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;

-- 代理人仅能查看自己的客户
CREATE POLICY customers_agent_access ON customers
  FOR SELECT
  USING (owner_id = current_setting('app.current_user_id')::uuid);

-- 团队主管可查看团队成员的客户
CREATE POLICY customers_team_leader_access ON customers
  FOR SELECT
  USING (owner_id IN (
    SELECT id FROM users WHERE team_id = current_setting('app.current_user_id')::uuid
  ));

-- 分公司管理员可查看本机构及下级的客户
CREATE POLICY customers_branch_admin_access ON customers
  FOR SELECT
  USING (owner_id IN (
    SELECT u.id FROM users u
    JOIN organizations o ON u.organization_id = o.id
    WHERE o.path LIKE (current_setting('app.current_org_path') || '%')
  ));

-- 总部管理员查看所有
CREATE POLICY customers_hq_access ON customers
  FOR ALL
  USING (current_setting('app.current_role_code') = 'HQ_ADMIN');
```

**RLS 应用范围**：
- `customers` — 客户数据隔离
- `customer_interactions` — 沟通记录隔离
- `customer_followups` — 跟进计划隔离
- `conversations` — AI 对话隔离
- `training_sessions` — 陪练记录隔离

### 7.4 最小权限原则

**数据库角色设计**：

| 角色 | 权限 | 说明 |
|------|------|------|
| `app_superuser` | ALL | 应用超级用户，仅运维使用 |
| `app_readwrite` | SELECT, INSERT, UPDATE, DELETE | 应用读写用户（不可 DDL） |
| `app_readonly` | SELECT | 只读用户（报表、分析） |
| `app_migration` | ALL (schema) | 迁移用户（仅 Alembic 使用） |

**连接安全**：
- 所有连接强制 SSL
- 密码认证 + 证书认证（生产环境）
- 连接池使用 PgBouncer，限制最大连接数

---

## 8. 数据迁移策略

### 8.1 Alembic 迁移管理

```
alembic/
├── versions/
│   ├── 001_init_extensions.py          # 启用 pgvector 扩展
│   ├── 002_create_organizations.py     # 机构表
│   ├── 003_create_roles_permissions.py # 角色权限
│   ├── 004_create_users.py             # 用户表
│   ├── 005_create_customers.py         # 客户管理
│   ├── 006_create_products.py          # 产品表
│   ├── 007_create_documents.py         # 知识文档
│   ├── 008_create_document_chunks.py   # 文档切片
│   ├── 009_create_conversations.py     # AI 对话
│   ├── 010_create_scripts.py           # 话术
│   ├── 011_create_training.py          # 陪练
│   ├── 012_create_community.py         # 社区
│   ├── 013_create_compliance.py        # 合规
│   ├── 014_create_ai_monitoring.py     # AI 监控
│   ├── 015_create_system.py            # 系统管理
│   ├── 016_create_indexes.py           # 索引
│   ├── 017_create_rls_policies.py      # 行级安全
│   └── 018_seed_data.py                # 种子数据
├── env.py
└── alembic.ini
```

**迁移规范**：
- 每次迁移文件包含 `upgrade()` 和 `downgrade()` 函数
- 禁止在迁移中直接修改数据（数据变更通过独立 seed 脚本）
- 生产环境迁移需经过 `staging` 环境验证
- 迁移版本号使用递增数字前缀，保证执行顺序

### 8.2 Seed 数据（生产环境必需）

| 数据 | 内容 | 迁移文件 |
|------|------|---------|
| 系统角色 | AGENT / TEAM_LEADER / BRANCH_ADMIN / HQ_ADMIN / SYSTEM_ADMIN | `seed_roles.py` |
| 系统权限 | 资源+操作组合（约 50 条） | `seed_permissions.py` |
| 角色-权限关联 | 各角色对应的权限分配 | `seed_role_permissions.py` |
| 系统配置 | AI模型参数、业务参数、功能开关 | `seed_configs.py` |
| 合规规则 | 8 类违规规则及关键词 | `seed_compliance_rules.py` |
| 机构层级 | 总部 → 分公司 → 支公司 | `seed_organizations.py` |
| 系统标签 | 客户标签分类（约 20 条） | `seed_tags.py` |

### 8.3 Mock 数据（开发/演示环境）

通过独立脚本 `scripts/seed_mock_data.py` 注入，支持幂等执行（重复运行不产生重复数据）。

> **Task 35 校准**：实际种子脚本为 `scripts/seed.py`（角色 7 / 权限 21 / 组织 6 / 演示用户 4 / 训练场景 23），全段 exists-check-skip 幂等；修复了角色-权限绑定插入缺失 `await` 导致绑定静默不落库的问题（backend-pg 回归测试 test_seed_idempotency.py 覆盖，PG 48 passed）。

**实现方式**：
- 使用 `INSERT ... ON CONFLICT DO NOTHING` 避免重复
- Mock 数据的 `id` 使用固定 UUID（便于开发和测试关联）
- 密码统一使用 `mock_password` 的 bcrypt 哈希
- 向量数据使用零向量或随机低维向量（开发环境不调 Embedding API）

---

## 9. Demo 数据清单

> 以下为演示环境预置数据的完整清单，确保系统开箱即可展示完整功能。

### 9.1 用户数据（14 人）

| 角色 | 数量 | 说明 |
|------|------|------|
| 总部管理员 (HQ_ADMIN) | 1 | 超级管理员，拥有所有权限 |
| 分公司管理员 (BRANCH_ADMIN) | 1 | 管理分公司下所有代理人和数据 |
| 团队主管 (TEAM_LEADER) | 2 | 各管理 5 名代理人，可查看团队数据 |
| 代理人 (AGENT) | 10 | 一线销售人员，Demo 模式用户 |

**用户详情**：
- 总部管理员：admin@anzhenbao.com / 张管理
- 分公司管理员：branch@anzhenbao.com / 李经理
- 团队主管 A：leader1@anzhenbao.com / 王主管（团队 5 人）
- 团队主管 B：leader2@anzhenbao.com / 赵主管（团队 5 人）
- 代理人 1-5：属于王主管团队
- 代理人 6-10：属于赵主管团队
- 所有用户密码统一为 `Azb@2024demo`

### 9.2 客户数据（20 人）

| 客户类型 | 数量 | 说明 |
|---------|------|------|
| 慢病客户 (chronic_disease) | 5 | 高血压、糖尿病等慢病患者 |
| 老年客户 (elderly) | 5 | 60 岁以上老年群体 |
| 家庭客户 (family) | 5 | 有家庭保障需求的客户 |
| 标准客户 (standard) | 5 | 常规客户 |

**销售阶段分布**：
- 新线索 (new_lead)：3 人
- 初次接触 (first_contact)：3 人
- 需求了解 (need_discovery)：4 人
- 方案报价 (proposal)：3 人
- 异议处理 (objection_handling)：2 人
- 促成 (closing)：2 人
- 成交 (closed_won)：2 人
- 跟进 (follow_up)：1 人

### 9.3 产品数据（2 个）

| 产品 | 类型 | 说明 |
|------|------|------|
| 安诊保·慢病版 | chronic_disease | 针对慢病人群的健康险产品 |
| 安诊保·老年版 | elderly | 针对老年人群的综合保障产品 |

每个产品包含 1 个活跃版本、完整的保障条款和费率表。

### 9.4 知识文档（30 篇）

| 分类 | 数量 | 说明 |
|------|------|------|
| 产品条款 | 6 | 2 个产品 × 3 种文档（条款、费率表、投保须知） |
| 产品FAQ | 4 | 常见问题解答 |
| 销售培训材料 | 5 | 销售技巧、话术指南 |
| 核保规则 | 3 | 各类核保标准与流程 |
| 理赔指南 | 3 | 理赔流程与案例 |
| 竞品对比 | 3 | 市场竞品分析报告 |
| 健康知识 | 3 | 慢病管理、老年健康知识 |
| 政策法规 | 3 | 保险行业最新政策法规 |

每篇文档均已执行 RAG 预处理（分片、向量化），文档切片总计约 **500+ 条**。

### 9.5 陪练场景（20+ 个）

| 难度 | 数量 | 示例场景 |
|------|------|---------|
| 简单 (easy) | 7 | 基础产品介绍、需求探寻、客户关系建立 |
| 中等 (medium) | 8 | 价格异议处理、竞品对比应对、客户犹豫引导 |
| 困难 (hard) | 5+ | 多重异议组合、高净值客户、复杂家庭方案 |

**场景类型覆盖**：
- 价格异议 (price_objection)：4 个
- 需求异议 (need_objection)：3 个
- 决策异议 (decision_objection)：3 个
- 信任异议 (trust_objection)：3 个
- 竞品异议 (competitor_objection)：2 个
- 慢病客户场景 (chronic_disease)：2 个
- 老年客户场景 (elderly_care)：2 个
- 家庭规划 (family_plan)：1 个
- 交叉销售 (cross_sell)：1 个

### 9.6 话术数据（30 条）

| 分类 | 数量 | 说明 |
|------|------|------|
| 开场白 (opening) | 4 | 各类客户的破冰话术 |
| 需求探寻 (need_discovery) | 6 | 挖掘客户需求和痛点 |
| 产品介绍 (product_intro) | 6 | 产品亮点和价值传递 |
| 异议处理 (objection_handling) | 8 | 各类异议的应对话术 |
| 促成 (closing) | 3 | 促成签单技巧 |
| 跟进 (follow_up) | 3 | 售后与持续跟进话术 |

### 9.7 社区内容（30 条）

| 类型 | 数量 | 说明 |
|------|------|------|
| 经验分享 (experience) | 8 | 优秀销售经验心得 |
| 话术分享 (script) | 6 | 实用话术案例 |
| 成功案例 (case) | 5 | 成功签单案例分析 |
| 问答 (question) | 4 | 业务问题讨论 |
| 销售技巧 (tip) | 4 | 销售小技巧分享 |
| 庆祝 (celebration) | 3 | 业绩达成庆祝帖 |

每条帖子附带 2-5 条评论，总计约 **80+ 条评论**和 **50+ 条点赞**。

### 9.8 跟进记录（20 条）

| 状态 | 数量 | 说明 |
|------|------|------|
| 已完成 (completed) | 12 | 历史跟进记录，有详细结果 |
| 待跟进 (pending) | 5 | 未来 7 天内的待办跟进 |
| 已逾期 (overdue) | 3 | 超过计划时间的跟进任务 |

### 9.9 AI 操作记录（50 条）

| 类型 | 数量 | 说明 |
|------|------|------|
| product_qa（产品问答） | 20 | 产品知识查询记录 |
| script_gen（话术生成） | 10 | AI 话术生成记录 |
| customer_analysis（客户分析） | 8 | 客户画像分析记录 |
| training（陪练） | 7 | AI 陪练记录 |
| summarization（摘要） | 5 | 内容摘要记录 |

每条记录包含完整的 Token 用量、延迟数据、RAG 来源信息。

### 9.10 其他预置数据

| 数据 | 数量 | 说明 |
|------|------|------|
| 合规规则 | 8 | 8 类违规规则，每类 3-10 个关键词 |
| 系统配置 | 15 | AI 参数、业务参数、功能开关 |
| 客户标签 | 20 | 系统预置标签 |
| 客户沟通记录 | 30+ | 与跟进记录配套的沟通详情 |
| 通知 | 15 | 各类系统通知示例 |
| 审计日志 | 100+ | 覆盖各种操作类型的审计记录 |

---

## 附录 A：表清单总览

| 序号 | 表名 | 中文 | 分类 | 说明 |
|------|------|------|------|------|
| 1 | users | 用户表 | 用户与权限 | 系统用户（代理人、管理员等） |
| 2 | roles | 角色表 | 用户与权限 | 角色定义 |
| 3 | permissions | 权限表 | 用户与权限 | 细粒度权限项 |
| 4 | role_permissions | 角色权限关联表 | 用户与权限 | 多对多中间表 |
| 5 | organizations | 机构表 | 用户与权限 | 组织架构（树形） |
| 6 | customers | 客户表 | 客户管理 | 客户信息与画像 |
| 7 | customer_tags | 客户标签表 | 客户管理 | 标签标准化定义 |
| 8 | customer_interactions | 客户沟通记录表 | 客户管理 | 沟通详情 |
| 9 | customer_followups | 客户跟进计划表 | 客户管理 | 跟进任务管理 |
| 10 | products | 产品表 | 产品与知识 | 保险产品 |
| 11 | product_versions | 产品版本表 | 产品与知识 | 产品版本历史 |
| 12 | documents | 知识文档表 | 产品与知识 | RAG 知识库 |
| 13 | document_versions | 文档版本表 | 产品与知识 | 文档版本历史 |
| 14 | document_chunks | 文档切片表 | 产品与知识 | 文本切片+向量嵌入 |
| 15 | knowledge_permissions | 知识权限表 | 产品与知识 | 知识访问控制 |
| 16 | conversations | AI 对话表 | AI 对话与话术 | 对话会话 |
| 17 | messages | 对话消息表 | AI 对话与话术 | 对话消息详情 |
| 18 | scripts | 话术模板表 | AI 对话与话术 | 销售话术 |
| 19 | script_versions | 话术版本表 | AI 对话与话术 | 话术版本历史 |
| 20 | training_scenarios | 陪练场景表 | AI 陪练 | 陪练场景定义 |
| 21 | training_sessions | 陪练会话表 | AI 陪练 | 陪练记录 |
| 22 | training_messages | 陪练消息表 | AI 陪练 | 陪练对话详情 |
| 23 | training_scores | 陪练评分表 | AI 陪练 | 多维度评分 |
| 24 | community_posts | 社区帖子表 | 社区 | 社区内容 |
| 25 | community_comments | 社区评论表 | 社区 | 帖子评论 |
| 26 | community_likes | 社区点赞表 | 社区 | 点赞记录 |
| 27 | compliance_rules | 合规规则表 | 合规 | 违规检测规则 |
| 28 | compliance_reviews | 合规审查记录表 | 合规 | 违规审查记录 |
| 29 | ai_requests | AI 请求监控表 | AI 监控 | 请求日志 |
| 30 | ai_feedback | AI 反馈表 | AI 监控 | 用户反馈 |
| 31 | notifications | 通知表 | 系统管理 | 系统通知 |
| 32 | audit_logs | 审计日志表 | 系统管理 | 操作审计 |
| 33 | system_configs | 系统配置表 | 系统管理 | 动态配置 |

**共计 33 张表**。

---

## 附录 B：公共触发器模板

```sql
-- 自动更新 updated_at 字段的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有业务表创建触发器
-- CREATE TRIGGER set_updated_at
--     BEFORE UPDATE ON {table_name}
--     FOR EACH ROW
--     EXECUTE FUNCTION update_updated_at_column();

-- 软删除触发器（可选，设置 deleted_at）
CREATE OR REPLACE FUNCTION set_deleted_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_deleted = true AND OLD.is_deleted = false THEN
        NEW.deleted_at = now();
    ELSIF NEW.is_deleted = false THEN
        NEW.deleted_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 附录 C：pgvector 扩展安装

```sql
-- 安装 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 验证安装
SELECT * FROM pg_extension WHERE extname = 'vector';
```

---

> **文档版本**：v1.0
> **最后更新**：2025年
> **维护者**：安诊保 AI 副驾 技术团队


---

## Production Ingestion 持久化（Task 20）

- 上传链路：`POST /api/v1/knowledge-bases/{kb_id}/documents/upload`（生产模式）
- 写入：`knowledge_bases`（document_count/total_chunks 递增）→ `documents`（status=published、
  content_text、chunk_count、published_at、metadata_）→ `document_chunks`（content、search_text、
  embedding Vector(1536)、metadata_ 含 document_id/document_title/section/product_type/
  organization_id/allowed_roles/version/effective dates/status）
- 事务：同一 AsyncSession 内 Document+Chunks 一次 commit；失败整体 rollback（不残留半成品）
- 幂等：document_id 已存在 → 删旧 chunks 重建（re-index）


---

## Knowledge Base CRUD 生产化（Task 21）

- 管理链路：`POST/GET/PUT/DELETE /api/v1/admin/knowledge-bases[/{kb_id}]`（生产模式走 Repository）
- Repository：`backend/app/repositories/knowledge_repository.py`（create/get/list/update/delete + name_exists + 可见性过滤）
- `knowledge_bases.allowed_roles` 列：`JSONB(none_as_null=True)` —— Python None 存 SQL NULL（全员语义，Task 17B）
- `knowledge_bases.metadata` 列：新增（alembic 0009_kb_metadata），创建/更新时携带扩展元数据
- `audit_logs.organization_id` 列：新增（alembic **0010_audit_log_org_scope**，Task 37b），审计行固化操作人组织归属，支撑组织范围隔离查询；索引 `ix_audit_logs_organization_id`；无 FK（审计行不因组织删除失效）
- 删除：物理删除（FK `ondelete=CASCADE` → documents → document_chunks）


---

## Document Management 生产化（Task 22）

- 管理链路：`GET/POST/DELETE /api/v1/admin/knowledge-bases/{kb_id}/documents[/{doc_id}[/publish|/unpublish]]`（生产模式走 Repository）
- Repository：`backend/app/repositories/document_repository.py`（create/get/list/delete/update_document_status/publish/unpublish + JOIN KB 可见性过滤）
- 级联：`documents.knowledge_base_id` FK CASCADE（Task 20/21 既有）→ `document_chunks.document_id` FK CASCADE → embedding 随 chunk 行删除（无孤儿）
- 状态机：`uploaded → parsing → parsed → reviewing → published`（publish 置 published + published_at/published_by；unpublish 置 draft）
- 计数：delete 同步回退 `knowledge_bases.document_count` / `total_chunks`

---

> **Task 37 — Audit Log 落库**：audit_logs 表（0006 创建 + 0007 补 request_id）现由 `repositories/audit_log_repository.py` 写入/查询；生产关键路径（KB/Document/Auth）与中间件广谱捕获均落库；`GET /admin/audit-logs` 生产分支读取真实数据。测试 `test_audit_log_pg.py` 6 用例（backend-pg 54 passed）。

## Database Backup & Restore（Task 38 · P1 B1）

### 实现（Pilot 级，Cloud Verified）

- `scripts/backup_database.sh`：`pg_dump --format=custom` 逻辑备份，带时间戳，输出目录 `AZB_BACKUP_DIR`，
  凭据仅环境变量注入（`AZB_DATABASE_URL`），失败非 0，打印安全摘要（size/sha256）。
- `scripts/restore_database.sh`：`pg_restore -d <conninfo> --clean --if-exists` 到干净目标库，恢复失败非 0。
- `scripts/verify_restored_db.py`：备份前基线快照 + 恢复后对比（关键表计数 / alembic_version / pgvector 维度）。
- `scripts/seed_backup_fixture.py`：合成业务数据（KB/Document/Chunk(1536-dim)/AuditLog），仅合成数据。
- `.github/workflows/database-backup-restore.yml`：PG16+pgvector 云端演练（migration → seed → fixture → backup →
  clean restore → verify → app health → 错误凭据非 0 → 无备份文件入 Git），push 仅限备份相关路径 / workflow_dispatch。

### 云端演练结果（24cc2b1，run 32344482596）

- baseline == restored（mismatches={}）：users 4 / roles 7 / role_permissions 84 / organizations 6 /
  knowledge_bases 1 / documents 1 / document_chunks 3 / audit_logs 1 / training_scenarios 23
- alembic_version：`0010_audit_log_org_scope`（恢复后一致）
- pgvector：chunks_with_embedding 3 / embedding_dims 1536（向量数据恢复成功）

### 保留策略与外部依赖（Accepted Limitation）

- 演练产物仅存 runner 临时目录（不进 Git）；CI 演练为覆盖式管理。
- **正式生产自动备份（每日/每小时）+ 独立持久化对象存储 + 加密 + retention 归档 + WAL 归档/PITR + 跨地域灾备
  为外部依赖**（需外部 scheduler / 云 DB 托管备份策略），本 Task 不伪造实现；部署侧接入见 deployment.md §8.3。
