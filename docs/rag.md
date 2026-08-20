# RAG 知识库架构文档 — 安诊保 AI 副驾

> **文档状态**：当前有效 · 生产链路已真实验证（Implemented/Validated/Planned 已区分）
> 最后校准：2026-08-17

---

## 0. 实现状态区分（2026-08-17）

| 能力 | 状态 | 验证方式 |
|------|------|----------|
| 文档入库（解析/分块/嵌入） | **Implemented** | seed 脚本 + 生产代码 |
| pgvector 向量检索（1536 维，HNSW） | **Implemented + Validated** | Task 12/13 修复 cosine_distance vector 字面量后 E2E 通过 |
| BM25 全文检索（tsvector GIN） | **Implemented + Validated** | `to_tsvector` 查询时转换（Task 12 修复） |
| RRF 融合（K=60，×100 对齐阈值） | **Implemented + Validated** | Task 12 修复分数量级后 E2E 通过 |
| 查询 embedding（生产向量检索接线） | **Implemented + Validated** | Task 12 修复 `pipeline.query` 缺失 query_embedding |
| Confidence Gate（HIGH/MEDIUM/LOW/NONE） | **Implemented + Validated** | E2E：医疗险 ALLOW / 车险 REFUSE |
| RAG Refusal（无依据拒答） | **Implemented + Validated** | E2E：极光量子保险 → 无参考来源 |
| Citation（来源/标题/章节/分数） | **Implemented + Validated** | Product QA 参考来源 + Script Citation UI（Task 13） |
| **产品边界（product_type 过滤）** | **Implemented + Validated** | Task 13：metadata 精确匹配→标题回退；PG 集成测试 + E2E |
| 查询重写/扩展（LLM 变体） | **Planned** | 设计见 §4.1，未实现 |
| Rerank（独立重排模型） | **Planned** | 当前用 RRF top-k，未接 rerank 模型 |
| **权限过滤（allowed_roles + 组织范围）** | **Implemented + Tested** | Task 17B：SQL WHERE 层过滤（test_role_filter.py / test_org_scope.py）+ PG 集成（test_permission_pg.py）；详见 [rag-permission-audit.md](rag-permission-audit.md) |
| 文档版本化审核流 | **Partial** | 迁移 0007 建表；完整审核 UI 未闭环 |

> 正文中的详细设计如与上表冲突，以「实现状态」为准。


## 1. 架构概述

### RAG 在产品中的核心地位

RAG（Retrieval-Augmented Generation，检索增强生成）是安诊保 AI 副驾的**第一优先级功能**，也是整个产品智能能力的基础设施。保险行业的核心特点是知识密集、合规要求严格、条款信息精确——代理人需要的不是一个「会聊天的 AI」，而是一个**基于公司自有知识库、能精准引用产品条款、绝不瞎编**的专业助手。

RAG 是以下所有 AI 功能的底层依赖：

| 上层功能 | 依赖 RAG 的方式 |
|----------|-----------------|
| 产品问答 | 直接检索产品条款、FAQ，生成带引用的解答 |
| 话术生成 | 检索合规话术模板和产品卖点，避免违规表述 |
| 客户分析 | 检索疾病核保规则、健康告知要求 |
| 培训考试 | 从知识库抽取题目素材 |
| 合规检查 | 对照合规知识库校验 AI 输出 |

### 设计原则

| 原则 | 说明 |
|------|------|
| **答案可追溯** | 每条 AI 回答必须附带来源引用（文档名 + 章节 + 页码），支持代理人点击查看原文 |
| **检索不到时拒答** | 当知识库中无相关内容时，AI 必须明确拒绝回答，禁止幻觉生成 |
| **权限过滤** | 不同角色/机构看到不同的知识内容，检索结果必须在权限范围内 |
| **版本管理** | 知识文档有版本生命周期，旧版本自动失效，新版本无缝切换 |
| **合规兜底** | 所有 AI 输出经过合规引擎检查，高风险内容需标注风险提示 |

---

## 2. 整体 Pipeline 架构

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                        安诊保 AI 副驾 — RAG 全链路架构                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           离线索引流程（Offline Indexing）                                │
│                                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐              │
│  │  Upload  │──▶│  Parse   │──▶│Normalize │──▶│Structure │──▶│  Chunk   │              │
│  │  文档上传  │   │  文档解析  │   │  文本归一化│   │  结构化   │   │  智能切分  │              │
│  │          │   │          │   │          │   │          │   │          │              │
│  │ PDF      │   │ PDF→Text │   │ 去噪/格式 │   │ 标题层级  │   │ 语义切分  │              │
│  │ DOCX     │   │ 表格识别  │   │ 编码统一  │   │ 章节拆分  │   │ 512 token│              │
│  │ PPTX     │   │ OCR(待定)│   │ 去除水印  │   │ 元数据提取│   │ overlap 50│              │
│  │ TXT/MD   │   │ 版本记录  │   │          │   │          │   │          │              │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └────┬─────┘              │
│                                                                      │                    │
│                                                                      ▼                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────────────────────────────┐              │
│  │  Index   │◀──│ Embed    │◀──│              Metadata 注入                 │              │
│  │  索引入库  │   │  向量化   │   │                                          │              │
│  │          │   │          │   │  product: "安诊保慢病版"                    │              │
│  │ pgvector │   │1536 维   │   │  document_name: "产品条款"                  │              │
│  │ HNSW 索引│   │ cosine   │   │  version: "2026-v1"                       │              │
│  │ GIN 索引 │   │ 批量处理  │   │  section: "健康告知"                       │              │
│  │          │   │          │   │  page: 5, effective_date, permission...   │              │
│  └──────────┘   └──────────┘   └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           在线查询流程（Online Query）                                    │
│                                                                                 │
│  用户问题："安诊保慢病版，高血压患者能不能买？需要哪些材料？"                             │
│        │                                                                                │
│        ▼                                                                                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────────────────┐           │
│  │ Query        │──▶│ Query        │──▶│         Hybrid Search               │           │
│  │ Understanding │   │ Rewrite +    │   │                                      │           │
│  │ 查询理解      │   │ Expand       │   │  ┌─────────────┐  ┌─────────────┐   │           │
│  │              │   │ 查询重写/扩展 │   │  │   Vector     │  │    BM25      │   │           │
│  │ · 意图识别    │   │              │   │  │   Search     │  │   Keyword    │   │           │
│  │ · 产品范围限定│   │ · 同义扩展    │   │  │   pgvector   │  │   GIN索引    │   │           │
│  │ · 实体提取    │   │ · 补全省略    │   │  │  cosine sim  │  │   tsvector   │   │           │
│  └──────────────┘   └──────────────┘   │  Top-K=20    │  │  Top-K=20   │   │           │
│                                        └──────┬──────┘  └──────┬──────┘   │           │
│                                               │                │          │           │
│                                               └───────┬────────┘          │           │
│                                                       ▼                   │           │
│                                        ┌──────────────────────────┐     │           │
│                                        │    RRF Fusion (K=60)     │     │           │
│                                        │  倒数排名融合，合并去重     │     │           │
│                                        └────────────┬─────────────┘     │           │
│                                                     ▼                   │           │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐     │           │
│  │Compliance    │◀──│  Citation    │◀──│     Rerank 重排序        │◀──┘           │
│  │  Check       │   │  引用标注    │   │                          │               │
│  │  合规检查    │   │  引用验证    │   │  · Rerank Model 评分    │               │
│  │              │   │  来源追溯    │   │  · 多维度相关性打分      │               │
│  │ · 敏感词检测  │   │              │   │  · 交叉编码器精排        │               │
│  │ · 风险等级   │   │  引用卡片:   │   │  · Top-N 筛选（N=5~8）   │               │
│  │ · 风险提示   │   │  [文档名+页码]│   │                          │               │
│  └──────┬───────┘   └──────────────┘   └──────────────────────────┘               │
│         │                                                                           │
│         ▼                                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │ Permission Filter 权限过滤                                                    │  │
│  │  按 user.role / organization 过滤检索结果，确保不越权                             │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│         │                                                                           │
│         ▼                                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          LLM 生成                                              │  │
│  │                                                                                │  │
│  │   System Prompt + 检索 Context（Top-N Chunks）+ 用户问题                         │  │
│  │                           │                                                      │  │
│  │                           ▼                                                      │  │
│  │   ┌────────────────────────────────────────────────────────────┐               │  │
│  │   │  "根据知识库，安诊保慢病版对高血压患者的核保要求如下：           │               │  │
│  │   │   1. 收缩压 ≤160mmHg 且舒张压 ≤100mmHg 可标准体承保 [1]     │               │  │
│  │   │   2. 需提供近 6 个月内体检报告 [2]                             │               │  │
│  │   │   3. 已有并发症者需人工核保 [1]                                │               │  │
│  │   │                                                           │               │  │
│  │   │   参考资料：                                                │               │  │
│  │   │   [1] 安诊保慢病版产品条款 v2026-1 · 健康告知 · 第5页          │               │  │
│  │   │   [2] 安诊保核保手册 · 高血压核保规则 · 第12页"                │               │  │
│  │   └────────────────────────────────────────────────────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│         │                                                                           │
│         ▼                                                                           │
│  ┌──────────────┐   ┌──────────────┐                                                │
│  │  Result      │──▶│   SSE        │────▶  前端（引用卡片 + 流式文本）                     │
│  │  最终结果    │   │  流式返回    │                                                │
│  └──────────────┘   └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 文档处理 Pipeline

### 3.1 文档上传

| 项目 | 规范 |
|------|------|
| **支持格式** | PDF、DOCX、PPTX、TXT、Markdown |
| **文件大小限制** | 单文件最大 50MB |
| **上传安全检查** | 文件类型校验（Magic Number，非仅扩展名）、病毒扫描（ClamAV / 待集成）、文件名安全过滤 |
| **存储位置** | 对象存储（S3/OSS），`documents/` 前缀路径 |
| **并发限制** | 同一用户最多同时上传 3 个文件 |

上传后文档初始状态为 `uploaded`，需要手动触发解析或自动进入解析流程。

### 3.2 文档解析

#### PDF 解析策略

```
PDF 输入
    │
    ├──▶ 文本层提取（PyMuPDF / pdfplumber）
    │       · 保留原始文本和布局信息
    │       · 提取页码信息
    │
    ├──▶ 表格识别（Camelot / pdfplumber.table）
    │       · 表格 → 结构化文本（Markdown 表格格式）
    │       · 保留行列关系
    │
    ├──▶ 图片 OCR（待确认 / Mock）
    │       · 扫描件 PDF → OCR 文字提取
    │       · 图片中的文字信息提取
    │       · Demo 阶段跳过，预留接口
    │
    └──▶ 保留溯源信息
            · document_id：文档唯一标识
            · page：页码
            · section：章节标题（解析后填充）
            · source_text：原始文本
```

#### DOCX / PPTX 解析策略

- **DOCX**：使用 `python-docx` 提取段落文本，识别标题样式（Heading 1~6）作为层级结构
- **PPTX**：使用 `python-pptx` 逐页提取文本框内容，每页作为一个逻辑单元，保留幻灯片序号

#### 解析输出规范

每段解析后的文本必须携带以下溯源信息：

```json
{
  "document_id": "uuid-xxx",
  "page": 5,
  "section": "健康告知",
  "source_text": "被保险人投保时需如实告知健康状况...",
  "element_type": "paragraph",
  "table_data": null
}
```

### 3.3 文档结构化

文档结构化是将线性文本转换为带有层级关系的结构化内容，是后续语义切分的基础。

#### 标题层级识别

| 策略 | 说明 |
|------|------|
| 样式识别 | 从 DOCX/PPTX 中提取标题样式（Heading 1~6）|
| 字体特征 | PDF 中通过字体大小、加粗特征推断标题层级 |
| 正则匹配 | 中文编号模式：`第一章`、`第一条`、`一、`、`（一）`、`1.`、`（1）` |
| 上下文推断 | 结合前后文语义辅助判断层级 |

#### 章节拆分

```
原始文档
    │
    ▼
标题层级树 (Heading Tree)
    │
    ├── 第一章 总则
    │     ├── 第一条 保险合同构成
    │     ├── 第二条 投保范围
    │     └── 第三条 保险责任
    ├── 第二章 健康告知
    │     ├── 第四条 告知义务
    │     └── 第五条 核保规则
    └── 第三章 保险金申请
```

#### 元数据提取

从文档内容中自动提取结构化元数据，注入每个 Chunk：

| 字段 | 来源 | 示例 |
|------|------|------|
| `product` | 关联产品 / 文档内容 | "安诊保慢病版" |
| `document_name` | 上传时指定 / 文件名 | "产品条款" |
| `version` | 上传时指定 / 文档内容 | "2026-v1" |
| `section` | 结构化识别 | "健康告知" |
| `page` | 解析时记录 | 5 |
| `effective_date` | 上传时指定 | "2026-08-01" |
| `permission` | 文档权限配置 | "AGENT" |
| `risk_level` | 合规规则标记 | "HIGH" |

### 3.4 Chunk 策略

#### 语义切分 vs 固定长度

系统支持两种切分策略，默认使用**语义切分**：

| 策略 | 原理 | 适用场景 |
|------|------|----------|
| **语义切分**（推荐） | 按段落、标题、列表等自然语义边界切分 | 产品条款、政策文档等结构化文档 |
| **固定长度** | 按 token 数量等分，带重叠窗口 | 非结构化文本、FAQ 等短文本集合 |

#### 参数配置

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `chunk_size` | 512 tokens | 256~1024 | 每个 Chunk 的目标 token 数 |
| `chunk_overlap` | 50 tokens | 20~100 | 相邻 Chunk 之间的重叠 token 数 |

#### 语义切分流程

```
结构化文档 (带标题层级)
    │
    ▼
按最低标题层级切分 → 检查每个段落的 token 数
    │
    ├── token ≤ 512 → 保留为一个 Chunk
    │
    ├── 512 < token ≤ 1024 → 按句号/分号拆分为子 Chunk
    │
    └── token > 1024 → 按固定长度切分 + overlap
    │
    ▼
Chunk 质量评估
    │
    ├── 过短 Chunk（< 50 tokens）→ 合并到相邻 Chunk
    ├── 过长 Chunk（> 800 tokens）→ 进一步拆分
    └── 无意义 Chunk（纯数字/标点）→ 丢弃
```

#### Chunk 必须保留的信息

每个 Chunk 必须保留 `page`（页码）和 `section`（章节标题），用于后续引用标注和用户溯源。

### 3.5 Metadata 注入

为每个 Chunk 注入标准 Metadata，存入 `document_chunks.metadata`（JSONB 字段）：

```json
{
  "product": "安诊保慢病版",
  "document_name": "产品条款",
  "version": "2026-v1",
  "section": "健康告知",
  "page": 5,
  "effective_date": "2026-08-01",
  "permission": "AGENT",
  "risk_level": "HIGH",
  "document_id": "doc_uuid_xxx",
  "chunk_index": 12,
  "total_chunks": 45
}
```

Metadata 在检索结果过滤和引用标注中发挥关键作用。

### 3.6 Embedding

#### 模型选型

| 模型 | 维度 | 语言支持 | 状态 |
|------|------|---------|------|
| `text-embedding-3-small`（OpenAI） | 1536 | 中英文 | **当前计划** |
| `bge-large-zh-v1.5`（BAAI） | 1024 | 中文优化 | 备选方案 |
| `MockEmbeddingProvider` | 1536 | — | Demo/开发模式 |

> **注意**：最终模型选型需根据实际测试效果确定。如果使用 `bge-large-zh`，需同步修改向量维度为 1024。

#### 批量 Embedding

- 批量大小：每次最多 100 个 Chunk
- 请求频率：遵守 API 速率限制（RPM/TPM）
- 失败重试：指数退避策略，最多重试 3 次
- 进度追踪：通过 `documents.status` 字段（`embedding` 状态）和进度计数器

#### Embedding 缓存

为避免重复计算，建立 Embedding 缓存机制：

```python
# 缓存 Key = hash(content + model_name + model_version)
# 缓存 Value = embedding vector (List[float])
# 存储位置：Redis，TTL = 永不过期（Embedding 不变）
# 命中缓存时直接返回，跳过 API 调用
```

### 3.7 索引

#### 向量索引：pgvector HNSW

```sql
-- 安诊保当前阶段推荐 HNSW 索引
CREATE INDEX idx_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

| 索引策略 | 适用场景 | 参数 |
|----------|---------|------|
| IVFFlat | 切片 < 10,000 条 | `lists = sqrt(行数)` |
| **HNSW**（推荐） | 切片 ≥ 10,000 条 | `m = 16, ef_construction = 64` |

#### 关键词索引：PostgreSQL GIN (tsvector)

```sql
-- 为 BM25 关键词检索添加全文搜索索引
ALTER TABLE document_chunks ADD COLUMN tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED;

CREATE INDEX idx_chunks_tsv ON document_chunks USING GIN (tsv);
```

#### Metadata 索引

```sql
-- 常用 Metadata 过滤条件建立 GIN 索引
CREATE INDEX idx_chunks_metadata ON document_chunks USING GIN (metadata);

-- 产品范围过滤
CREATE INDEX idx_chunks_metadata_product
    ON document_chunks USING GIN ((metadata->'product'));

-- 权限过滤
CREATE INDEX idx_chunks_metadata_permission
    ON document_chunks USING GIN ((metadata->'permission'));
```

---

## 4. 查询 Pipeline

### 4.1 查询理解

用户输入的原始问题需要经过理解与改写，才能获得更好的检索效果。

#### 查询重写（Query Rewrite）

| 策略 | 说明 | 示例 |
|------|------|------|
| 指代消解 | 将对话历史中的代词替换为实体 | 「**它**的等待期」→「安诊保慢病版的等待期」 |
| 口语规范化 | 将口语化表达转为正式表述 | 「高血压能买吗」→「高血压患者投保条件」 |
| 简写展开 | 将缩写展开为完整名称 | 「慢病版」→「安诊保慢病版」 |

#### 查询扩展（Query Expansion）

| 策略 | 说明 | 示例 |
|------|------|------|
| 同义词扩展 | 基于保险领域同义词库扩展 | 「免赔额」→「免赔额 / 起付线 / 自付额」 |
| LLM 改写 | 使用 LLM 生成多个查询变体 | 生成 2~3 个语义等价的查询 |
| 多查询检索 | 每个变体独立检索，结果合并 | 提升召回覆盖面 |

#### 产品范围限定

根据对话上下文中的 `product_id` 或 `knowledge_scope`，在检索时自动添加 Metadata 过滤：

```python
# 如果用户在安诊保慢病版的对话中提问
filters = {
    "product": "安诊保慢病版",
    "status": "published",
    "is_deleted": False
}
```

#### 产品边界（Task 13 已实现，2026-08-17）

话术生成的 RAG 检索必须携带产品边界，避免「同领域但错误产品」被语义召回为有效依据（如"车险"查询命中医疗险文档）：

- `Retriever.search / _vector_search / _bm25_search` 与 `DemoRetriever.search` 新增 `product_type` 参数
- `_product_boundary_condition(product_type)` 过滤条件（两路检索共用）：
  - 优先：chunk metadata `product_type` 精确匹配（JSONB `->>`，如 `metadata->>'product_type' = '医疗险'`）
  - 回退：metadata 缺失时按「文档标题包含产品名」匹配（`d.title LIKE '%医疗险%'`）
- 调用链：`script_service` 生成时把 `effective_product_type` 传入 `pipeline.query(product_type=...)` → `retriever.search`
- 效果：产品边界过滤后仍走 Confidence Gate（ALLOW / REVIEW / REFUSE）；错误产品返回空 → REFUSE 不生成话术
- 注意：确定性 E2E 知识库每个产品 ≥3 chunk（产品边界过滤后 count>=3 才能满足 Confidence Gate HIGH）

### 4.2 Hybrid Search

#### 向量检索（Cosine Similarity）

```sql
-- 向量相似度检索
SELECT dc.id, dc.content, dc.metadata,
       1 - (dc.embedding <=> $query_vector::vector) AS similarity
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE d.status = 'published'
  AND dc.is_deleted = false
  AND dc.metadata->>'product' = $product  -- 产品范围过滤
ORDER BY dc.embedding <=> $query_vector::vector
LIMIT 20;
```

#### BM25 关键词检索

```sql
-- BM25 全文检索
SELECT dc.id, dc.content, dc.metadata,
       ts_rank_cd(dc.tsv, query) AS bm25_score
FROM document_chunks dc, plainto_tsquery('simple', $query_text) query
JOIN documents d ON dc.document_id = d.id
WHERE dc.tsv @@ query
  AND d.status = 'published'
  AND dc.is_deleted = false
  AND dc.metadata->>'product' = $product
ORDER BY bm25_score DESC
LIMIT 20;
```

#### 结果融合：RRF（Reciprocal Rank Fusion）

使用 RRF 算法融合向量检索和 BM25 检索的结果：

```
RRF Score(d) = Σ  1 / (k + rank_i(d))

其中：
  d = 某个 Chunk
  rank_i(d) = 该 Chunk 在第 i 个检索结果中的排名
  k = 60（平滑常数，避免排名靠前的结果被过度放大）
```

**Top-K 参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 向量检索 Top-K | 20 | 向量相似度取前 20 |
| BM25 检索 Top-K | 20 | 关键词匹配取前 20 |
| RRF 融合后 Top-K | 20 | 融合排序后取前 20 进入 Rerank |

### 4.3 Rerank

#### Rerank 模型（待确认）

| 模型 | 说明 | 状态 |
|------|------|------|
| `bge-reranker-v2-m3` | BAAI 多语言重排序模型 | **计划方案** |
| `cohere-rerank` | Cohere Rerank API | 备选方案 |
| `MockReranker` | 基于 BM25 分数的 Mock 实现 | Demo 模式 |

> Demo 阶段使用 `MockReranker`，基于 BM25 + cosine score 的加权综合分。

#### 多维度评分

Rerank 模型对每个 Chunk 进行精细化的相关性评分：

```
Rerank Score = α × CrossEncoder_Score
             + β × BM25_Score
             + γ × Metadata_Match_Score
             + δ × Recency_Score

其中：
  CrossEncoder_Score：交叉编码器的语义相关性分数（0~1）
  BM25_Score：关键词匹配分数（归一化到 0~1）
  Metadata_Match_Score：产品/版本/章节匹配度
  Recency_Score：文档时效性（越新越高）
```

#### 权限过滤

Rerank 后、送入 LLM 前，执行权限过滤：

```python
async def filter_by_permission(chunks: list, user: User) -> list:
    """根据用户角色和机构过滤检索结果"""
    user_roles = get_user_roles(user.id)
    user_org = get_user_org(user.id)
    allowed_permissions = get_permission_set(user_roles, user_org)
    
    return [
        chunk for chunk in chunks
        if chunk.metadata["permission"] in allowed_permissions
        and is_org_allowed(chunk.metadata, user_org)
    ]
```

**过滤规则**：
- `AGENT`：所有代理人可见
- `TEAM_LEADER`：团队主管及以上可见
- `ADMIN`：仅管理员可见
- 机构级别：按 `knowledge_permissions` 表配置的机构访问规则过滤

### 4.4 LLM 生成

#### Prompt 构造

```python
SYSTEM_PROMPT = """
你是安诊保 AI 副驾，一位专业的保险产品知识助手。

## 核心规则
1. 只能基于下方提供的【知识库内容】回答问题，绝不能编造或推测。
2. 如果知识库中没有相关信息，必须明确告知用户"抱歉，知识库中暂未找到相关内容"，并建议咨询公司核保部门。
3. 每个关键信息点必须标注引用来源 [序号]。
4. 回答语言简洁专业，适合保险代理人使用。
5. 涉及核保、理赔、健康告知等内容时，务必提醒以官方条款为准。

## 知识库内容
{context}

## 引用来源
{sources}
"""
```

#### 结构化输出

要求 LLM 按以下结构输出：

```json
{
  "answer": "根据知识库，安诊保慢病版对高血压患者的核保要求如下...",
  "citations": [
    {
      "index": 1,
      "document_name": "安诊保慢病版产品条款",
      "version": "2026-v1",
      "section": "健康告知",
      "page": 5,
      "chunk_text": "被保险人收缩压≤160mmHg..."
    }
  ],
  "confidence": "high",
  "risk_level": "MEDIUM",
  "disclaimer": "以上信息仅供参考，具体以保险合同条款为准。"
}
```

#### 引用标注

- 在回答文本中使用 `[1]`、`[2]` 等序号标注引用来源
- 序号与下方 `citations` 数组中的条目一一对应
- 前端渲染时将序号转为可点击的引用卡片

### 4.5 后处理

#### 引用验证

```python
async def validate_citations(answer: str, citations: list, context_chunks: list) -> bool:
    """验证 LLM 生成的引用是否真实存在于检索结果中"""
    for citation in citations:
        # 检查引用的 chunk_text 是否来自真实的检索结果
        matched = any(
            citation["chunk_text"][:50] in chunk.content
            for chunk in context_chunks
        )
        if not matched:
            return False  # 引用不合法，拒绝返回
    return True
```

#### 合规检查

通过合规引擎对 AI 输出进行自动检查：

| 检查项 | 规则 | 动作 |
|--------|------|------|
| 敏感词检测 | 包含"保证收益""稳赚不赔"等禁用词 | 标记为高风险，添加风险提示 |
| 承诺性表述 | 包含"一定赔""100%报销"等绝对化表述 | 标记为高风险 |
| 条款准确性 | 引用内容与原文偏差过大 | 触发人工审核 |
| 风险提示缺失 | 涉及核保/理赔时未加免责声明 | 自动追加免责提示 |

#### 风险提示

根据检查结果，在回答末尾自动追加风险提示：

```
⚠️ 以上信息仅供参考，具体保障内容和责任免除以保险合同条款为准。
涉及健康告知和核保问题，请以公司最新核保规则为准。
```

---

## 5. 知识库管理

### 5.1 知识生命周期

```
  上传        解析        草稿        审核        发布        生效        失效
  (Upload)  (Parse)    (Draft)   (Review)   (Publish)  (Active)  (Expired)
    │          │          │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼          ▼          ▼
  uploaded   parsing   parsed   reviewing  published   active    expired
    │          │          │          │          │          │          │
    │     Chunk+Metadata  人工审核   管理员     Embedding   effective  expiry
    │     注入+预览       Chunk     审核通过   索引入库   _date 到达  _date 到达
    │                     质量检查   发布操作   可被检索              不再检索
    │                                                                 保留历史
    │                                                                  可追溯
```

**各阶段操作说明**：

| 阶段 | 可执行操作 | 说明 |
|------|-----------|------|
| `uploaded` | 解析、删除 | 文件已上传到对象存储，等待解析 |
| `parsing` | 等待 | 正在执行文档解析 + Chunk 切分 |
| `parsed` | 查看 Chunk、编辑 Chunk、提交审核、删除 | 解析完成，可人工审核 Chunk 质量 |
| `reviewing` | 通过/驳回 | 审核人逐条审核 Chunk 或批量通过 |
| `published` | 过期、重新切分、重新 Embedding | 已发布，Embedding 完成，可被 AI 检索 |
| `expired` | 重新发布 | 已失效，不再参与检索，保留历史记录 |

### 5.2 版本管理

- **版本号规范**：`{年份}-v{序号}`，例如 `2026-v1`、`2026-v2`
- **新版本发布后旧版本自动失效**：发布新版本时，系统自动将同一 `document_id` 下的旧版本状态置为 `expired`
- **版本追溯**：通过 `document_versions` 表记录完整版本历史，支持版本间对比
- **Chunk 关联版本**：每个 Chunk 记录 `document_version_id`，确保检索结果可追溯到具体版本

### 5.3 权限管理

通过 `knowledge_permissions` 表实现知识条目的细粒度权限控制：

| 维度 | 说明 |
|------|------|
| 角色维度 | 按 `role_id` 控制（AGENT / TEAM_LEADER / ADMIN）|
| 机构维度 | 按 `organization_id` 控制（总部 / 分公司 / 支公司）|
| 权限类型 | `view`（查看/检索）、`edit`（编辑）、`approve`（审核发布）|

检索时自动根据当前用户的角色和机构过滤结果，确保不越权访问。

### 5.4 质量监控

#### Chunk 级别指标

| 指标 | 数据来源 | 用途 |
|------|---------|------|
| 召回次数（recall_count） | `document_chunks` 被检索命中的次数 | 识别高频/低频 Chunk |
| 使用次数（usage_count） | 引用到最终回答中的次数 | 评估 Chunk 实际价值 |
| 错误反馈次数（error_count） | 用户点击「回答有误」时关联的 Chunk | 定位低质量 Chunk |

#### 文档级别指标

| 指标 | 说明 |
|------|------|
| 召回率 | 文档中 Chunk 被检索命中的比例 |
| 覆盖度 | 文档 Chunk 在各类查询中的分布情况 |
| 时效性 | 文档距上次更新的时间 |

#### 定期清理

- 每月生成质量报告，标记长期零召回的文档
- 超过 6 个月未被召回的 `expired` 文档建议归档
- 错误反馈率超过 30% 的 Chunk 触发人工复审

---

## 6. 向量数据库设计

### pgvector 扩展配置

```sql
-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 设置向量精度（可选）
SET ivfflat.probes = 10;   -- IVFFlat 探测数
SET hnsw.ef_search = 40;   -- HNSW 搜索宽度
```

### 向量维度

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 向量维度 | **1536** | 对应 OpenAI `text-embedding-3-small` 输出维度 |
| 距离度量 | **cosine** | 余弦相似度，`<=>` 运算符 |

> 如果切换为 `bge-large-zh`，需修改为 1024 维，并重建所有索引。

### 索引类型

| 阶段 | 切片数量 | 索引类型 | 参数 |
|------|---------|---------|------|
| Demo / 早期 | < 10,000 | IVFFlat | `lists = sqrt(行数)` |
| **生产推荐** | ≥ 10,000 | **HNSW** | `m = 16, ef_construction = 64` |
| 大规模 | > 500,000 | HNSW (高精度) | `m = 32, ef_construction = 100` |

### 查询优化

```sql
-- 优化 1：仅查询已发布文档的 Chunk（部分索引）
CREATE INDEX idx_chunks_published
ON document_chunks (document_id)
WHERE is_deleted = false;

-- 优化 2：产品范围 + 状态联合过滤
CREATE INDEX idx_chunks_product_published
ON document_chunks ((metadata->>'product'))
WHERE is_deleted = false;

-- 优化 3：HNSW ef_search 动态调整
-- 简单查询：ef_search = 40（速度快）
-- 精确查询：ef_search = 100（精度高）
SET LOCAL hnsw.ef_search = 40;
```

---

## 7. RAG 与 AI 产品专家的集成

### API 调用流程

```
前端 (React)                     后端 (FastAPI)                     RAG Pipeline
    │                                │                                │
    │  POST /api/v1/ai/chat          │                                │
    │  {message, product_id,         │                                │
    │   knowledge_scope}             │                                │
    │───────────────────────────────▶│                                │
    │                                │  1. 查询理解 + 重写              │
    │                                │  2. Hybrid Search               │
    │                                │  3. Rerank                      │
    │                                │  4. 权限过滤                    │
    │                                │  5. 构造 Prompt                  │
    │                                │  6. LLM 生成                    │
    │                                │  7. 合规检查                    │
    │                                │                                │
    │  SSE: data: {"type":"token",  │                                │
    │         "content":"根据..."}   │                                │
    │◀═══════════════════════════════│                                │
    │                                │                                │
    │  SSE: data: {"type":"sources",│                                │
    │         "sources":[...]}       │                                │
    │◀═══════════════════════════════│                                │
    │                                │                                │
    │  SSE: data: {"type":"done",   │                                │
    │         "latency_ms":1200}     │                                │
    │◀═══════════════════════════════│                                │
```

### SSE 流式返回

SSE 事件类型定义：

| 事件类型 | 说明 | 数据结构 |
|----------|------|----------|
| `token` | 流式文本 token | `{"type": "token", "content": "根"}` |
| `sources` | 引用来源列表 | `{"type": "sources", "sources": [{"document_id", "title", "relevance", "chunk_text"}]}` |
| `done` | 生成完成 | `{"type": "done", "latency_ms": 1200, "total_tokens": 356}` |
| `error` | 错误信息 | `{"type": "error", "code": "RAG_001", "message": "知识库未找到相关内容"}` |

### 引用卡片数据结构

```typescript
// 前端引用卡片类型定义
interface CitationCard {
  index: number;                // 引用序号 [1], [2]...
  document_id: string;          // 文档 ID
  document_name: string;        // 文档名称："安诊保慢病版产品条款"
  version: string;              // 版本号："2026-v1"
  section: string;              // 章节："健康告知"
  page: number;                 // 页码：5
  relevance: number;            // 相关性分数：0.95
  chunk_text: string;           // 引用的原文片段
  risk_level?: string;          // 风险等级（可选）
}
```

### 拒答机制

当检索结果为空或相关性分数低于阈值时，触发拒答：

```python
REFUSAL_THRESHOLD = 0.3  # 相关性分数阈值

async def check_refusal(reranked_chunks: list) -> bool:
    """检查是否应该拒答"""
    if not reranked_chunks:
        return True
    if reranked_chunks[0].score < REFUSAL_THRESHOLD:
        return True
    return False

# 拒答时的响应
REFUSAL_RESPONSE = {
    "answer": "抱歉，知识库中暂未找到与您问题相关的信息。建议您：\n"
              "1. 尝试换一种方式描述问题\n"
              "2. 咨询公司核保/理赔部门获取准确信息\n"
              "3. 查看相关产品条款原文",
    "citations": [],
    "confidence": "none",
    "is_refusal": True
}
```

**拒答原则**：宁可拒答，不可幻觉。这是安诊保 AI 副驾在保险行业场景下的核心安全底线。

---

## 8. Demo/Mock 模式

为支持无外部 API 依赖的开发和演示，系统提供完整的 Mock 实现。

### MockEmbeddingProvider

```python
class MockEmbeddingProvider:
    """生成确定性的伪向量，用于开发和测试"""
    
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
    
    async def embed_text(self, text: str) -> list[float]:
        # 基于文本内容生成确定性哈希向量
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # 扩展到目标维度
        vector = []
        for i in range(self.dimension):
            byte_index = i % len(hash_bytes)
            vector.append((hash_bytes[byte_index] - 128) / 128.0)
        # 归一化
        norm = sum(v**2 for v in vector) ** 0.5
        return [v / norm for v in vector]
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(t) for t in texts]
```

### 预设知识库

Demo 模式下预置以下知识文档，无需真实 Embedding 即可体验完整 RAG 流程：

| 文档 | 内容 | Chunk 数量 |
|------|------|-----------|
| 安诊保慢病版产品条款 | 保险责任、免责条款、等待期、健康告知 | 30 |
| 安诊保核保手册 | 常见疾病核保规则、体检要求 | 20 |
| 安诊保理赔指南 | 理赔流程、所需材料、时效规定 | 15 |
| 保险法基础知识 | 保险法核心条款、合规要求 | 10 |

### 预设检索结果

```python
MOCK_SEARCH_RESULTS = {
    "高血压": {
        "chunks": [
            {
                "content": "被保险人收缩压≤160mmHg且舒张压≤100mmHg，无并发症，可标准体承保。",
                "metadata": {"product": "安诊保慢病版", "section": "健康告知", "page": 5},
                "score": 0.95
            },
            {
                "content": "高血压患者需提供近6个月内二级及以上医院的体检报告，包含血压测量记录。",
                "metadata": {"product": "安诊保核保手册", "section": "高血压核保规则", "page": 12},
                "score": 0.88
            }
        ]
    },
    "等待期": { ... },
    "免赔额": { ... }
}
```

---

## 9. 性能优化

### 缓存策略

| 缓存对象 | 存储位置 | TTL | 说明 |
|----------|---------|-----|------|
| Embedding 结果 | Redis | 永不过期 | 相同文本 + 模型 → 相同向量 |
| 检索结果 | Redis | 5 分钟 | 相同查询 + 产品范围 → 相同检索结果 |
| LLM 回答 | Redis | 10 分钟 | 相同检索上下文 + 问题 → 相同回答 |
| 文档解析结果 | PostgreSQL | 永不过期 | 解析后的结构化文本，避免重复解析 |

### 批量处理

- **文档上传**：支持批量上传（最多 10 个文件），后台队列依次处理
- **Embedding**：批量发送请求（100 个/批），减少 API 调用次数
- **索引构建**：批量插入 `document_chunks`（1000 条/批），使用 `COPY` 替代逐条 `INSERT`

### 异步索引

文档解析和 Embedding 是耗时操作，必须异步执行：

```
同步：上传文件 → 返回 document_id + status=parsing
异步：后台 Celery/asyncio Task → Parse → Chunk → Embed → Index
回调：更新 documents.status = published + 通知前端
```

### 查询优化

| 优化手段 | 说明 | 预期效果 |
|----------|------|----------|
| HNSW ef_search 调优 | 根据查询场景动态调整 | 平衡速度与精度 |
| 并行检索 | 向量检索和 BM25 检索并行执行 | 总检索时间减少 40%~50% |
| 预过滤 | 先按 Metadata 过滤再执行向量检索 | 减少向量计算量 |
| 查询缓存 | 相同查询命中缓存直接返回 | 热门问题 P99 < 200ms |

---

## 10. 监控指标

### 检索性能指标

| 指标 | 计算方式 | 目标值 |
|------|---------|--------|
| 检索总耗时 | 从 Query 到 Rerank 完成 | P50 < 200ms，P99 < 500ms |
| 向量检索耗时 | Embedding 查询 + 相似度计算 | P50 < 100ms |
| BM25 检索耗时 | 全文搜索查询 | P50 < 50ms |
| Rerank 耗时 | 重排序计算 | P50 < 100ms |
| 端到端响应耗时 | 从用户发送到收到完整回答 | P50 < 3s，P99 < 8s |

### 检索质量指标

| 指标 | 计算方式 | 目标值 |
|------|---------|--------|
| 检索命中率 | 成功返回结果的查询 / 总查询 | > 90% |
| 引用准确率 | 引用内容与原文一致的比例 | > 95% |
| 拒答率 | 触发拒答的查询比例 | < 15%（正常范围内）|
| 幻觉率 | 生成内容无法追溯到知识库的比例 | **0%**（零容忍） |

### 用户满意度指标

| 指标 | 数据来源 | 说明 |
|------|---------|------|
| 有帮助反馈率 | `messages.feedback = 'helpful'` | 用户主动标记有帮助的比例 |
| 无帮助反馈率 | `messages.feedback = 'unhelpful'` | 触发人工复审的信号 |
| 对话完成率 | 有 AI 回复的对话 / 总对话 | 反映系统可用性 |
| 平均交互轮数 | 每次对话的消息数量 | 反映问题解决效率 |

### 告警规则

| 告警项 | 阈值 | 级别 |
|--------|------|------|
| 检索耗时 P99 > 1s | 持续 5 分钟 | WARNING |
| 检索命中率 < 80% | 持续 30 分钟 | CRITICAL |
| 幻觉率 > 0% | 任意一次 | CRITICAL |
| Embedding API 错误率 > 5% | 持续 10 分钟 | WARNING |
| 拒答率 > 30% | 持续 1 小时 | WARNING（可能知识库覆盖不足）|

---

## 附录：关键数据流

### A. 文档发布数据流

```
管理员上传文档
    → POST /api/v1/admin/knowledge/documents/upload
    → 文件存储到 S3/OSS
    → documents 表插入记录 (status=uploaded)
    → 返回 document_id

管理员触发解析
    → POST /api/v1/admin/knowledge/documents/:id/parse
    → 后台 Task：解析文档 → 结构化 → 语义切分
    → document_versions 插入版本记录
    → document_chunks 插入切片记录 (无 embedding)
    → documents.status = parsed
    → 返回 estimated_chunks

管理员审核通过
    → POST /api/v1/admin/knowledge/documents/:id/submit-review
    → documents.status = reviewing
    → 审核人确认

管理员发布
    → POST /api/v1/admin/knowledge/documents/:id/publish
    → 批量 Embedding (document_chunks.embedding 填充)
    → 旧版本 status = expired
    → documents.status = published
    → 返回 embedded_chunks
    → 知识可被检索
```

### B. 用户查询数据流

```
用户发送问题
    → POST /api/v1/ai/chat (SSE)
    → 查询理解 + 重写
    → Hybrid Search (Vector + BM25, 各 Top-20)
    → RRF 融合 (Top-20)
    → Rerank (Top-5~8)
    → 权限过滤
    → 检查是否需要拒答
    → 构造 Prompt (System + Context + Question)
    → LLM 流式生成
    → 引用验证 + 合规检查
    → SSE 逐 token 返回前端
    → SSE 返回引用卡片
    → 记录 messages + 更新 recall_count
```

---

## 6. 权限过滤（Task 17B 加固）

> 完整审计与修复锚点见 [docs/rag-permission-audit.md](rag-permission-audit.md)。
> 目标：**一个没有权限的人，物理上无法通过 RAG（召回、citation、SSE、日志正文）获得越权知识。**

### 6.1 实现摘要

| 维度 | 实现 | 状态 |
|------|------|------|
| Role filtering（allowed_roles） | SQL WHERE 层 `allowed_roles IS NULL OR allowed_roles ? role_code`（jsonb 存在），召回前过滤 | **Implemented + Tested**（test_role_filter.py） |
| Organization filtering（org scope） | `KnowledgeBase.organization_id IN (accessible_org_ids)`（`DataPermissionChecker.filter_accessible_org_ids()` 产出，`["__ALL__"]`=全量）；org=NULL=未限定组织的共享知识库 | **Implemented + Tested**（test_org_scope.py） |
| Citation leakage | citation 仅从过滤后的 `search_results` 构造；越权文档不出现在 reference_sources | **Protected**（test_citation_leak.py） |
| SSE leakage | `rag_context` / `style_complete` 引用来源与 citation 同源（过滤后集合） | **Protected**（test_citation_leak.py） |
| Prompt Injection | 消毒后检索仍受权限边界约束；HIGH 级注入直接拒答 | **Cannot bypass permission boundary**（test_permission_pg.py::J） |
| 拒答不降级 | 过滤后空结果 → 固定拒答文本，不 fallback 到通用模型知识 | **Implemented + Tested**（test_citation_leak.py::K） |

### 6.2 权限链（全栈生效）

```
User → Auth(JWT) → RBAC → Org Scope(DataPermissionChecker) → KB Scope(role)
→ Document Scope → Retrieval(SQL WHERE) → Confidence Gate → LLM → Citation → Compliance
```

任一层拒绝，知识不得进入最终回答。

### 6.3 实现要点

- 过滤时机：`_vector_search` / `_bm25_search` 的 **SQL WHERE 层**（JOIN KnowledgeBase），与 `product_type`、`effective_date`、`status=='published'` 同级，禁止"先召回全部再 Python 过滤"。
- 纵深防御：`Retriever._filter_by_permission` 保留原签名并填充真实逻辑（召回后二次校验，基于结果携带的 `kb_allowed_roles` / `kb_org_id` 元数据），日志仅记录 `filtered_count`，不记录被过滤正文。
- 调用方：`ProductQaService._real_chat/_demo_chat`、`ScriptService._production_generate_scripts` 均补传 `user_roles` / `org_id` / `accessible_org_ids`；无用户上下文时 `user_roles=[]`（全拒）。
- Demo 模式：`DemoRetriever` 实现等价过滤（chunk 携带 `kb_allowed_roles` / `kb_org_id`）。
- 偏差记录：任务段4 矩阵假设"HQ_ADMIN 命中 allowed_roles=['AGENT'] 的 KB"，与 §2.3.3 精确匹配硬约束冲突 → 以硬约束（精确匹配）为准，详见审计文档 §2 偏差记录。


---

## 7. Production Ingestion（Task 20）

> 状态：**Implemented + Tested**（PG 集成 tests/rag/test_ingestion_pg.py，CI backend-pg 纳入）

### 7.1 真实链路

```
管理员/系统上传 → POST /api/v1/knowledge-bases/{kb_id}/documents/upload
  → DocumentParser.parse → chunk_document → AIGateway.embed（真实 embedding，1536 维）
  → Document + DocumentChunk(embedding) 写入 PostgreSQL + pgvector
  → metadata（document_id/document_title/section/product_type/organization_id/
     allowed_roles/version/effective dates/status）→ status=published
  → Retriever（SQL WHERE 层权限过滤）→ RAG context → Citation
```

### 7.2 关键保证

| 项 | 实现 |
|----|------|
| 持久化 | `pipeline._persist_production`：Document / DocumentChunk / embedding（Vector 1536）全部落库 |
| 事务安全 | 解析/embedding/DB 任一失败 → `session.rollback()` 后抛出，不残留 document 或部分 chunks |
| 空文档 | 解析后无有效内容 → ValueError（400），不留半成品 |
| 重复索引 | 同 document_id 重复 index → 删除旧 chunks 重建（幂等），KB document_count 不重复累加 |
| 权限 metadata | chunk/document metadata 继承 KB 的 allowed_roles / organization_id，与 Task 17B SQL WHERE 层过滤一致 |
| embedding 复用 | 经 AIGateway/provider 契约（不绑定 SDK），维度与 pgvector 列（1536）一致 |
| 产品边界 | product_type 写入 metadata，检索按产品过滤（错误产品不召回） |

### 7.3 边界（如实声明）

- 已实现/已验证：新文档经真实 ingestion 后可被 Retriever 在 PG/pgvector 检索命中，
  权限边界（AGENT@A 可见 / HQ_ADMIN 角色拒绝 / AGENT@B 组织拒绝）由集成测试固化。
- 已实现（后续 Task 收敛，历史记录见对应 audit）：知识库 CRUD 已生产化（Task 21，DB backed + 权限继承）；文档管理已生产化（Task 22）；上传大小限制 10MB（Task 34）；上传仍需要知识库上下文（真实）
  已存在于 DB（seed/生产创建）；"管理员上传链路"与"已有 seed 知识可检索"是两件事，
  前者为本次闭环（接口 + 持久化 + 检索 + 测试），后者为 Task 12/13 既有能力。


---

## 8. Knowledge Base CRUD Production 化（Task 21）

> 状态：**Implemented + Tested**（PG 集成 tests/knowledge/test_kb_crud.py 7 用例，CI backend-pg 纳入）

### 8.1 CRUD 全链路 DB backed

```
管理员 → POST   /api/v1/admin/knowledge-bases          → DB insert（KnowledgeBaseRepository）
      → GET    /api/v1/admin/knowledge-bases          → DB query（角色+组织可见性过滤）
      → GET    /api/v1/admin/knowledge-bases/{kb_id}  → DB query（越权/不存在 → 404）
      → PUT    /api/v1/admin/knowledge-bases/{kb_id}  → DB update（写权限：管理角色或创建者）
      → DELETE /api/v1/admin/knowledge-bases/{kb_id}  → DB 物理删除（FK CASCADE 级联文档/chunk）
```

### 8.2 关键保证

| 项 | 实现 |
|----|------|
| Repository 层 | `repositories/knowledge_repository.py`（SQLAlchemy async，API 层不直接操作 ORM） |
| 可见性过滤 | `allowed_roles IS NULL OR ? role`（角色）+ `organization_id IS NULL OR IN accessible_org_ids`（组织），与 Task 17B 检索语义一致；SYSTEM_ADMIN `__ALL__` 跳过组织过滤 |
| 权限继承 | 创建支持 `organization_id`/`allowed_roles`/`metadata`；显式指定组织需管理角色；写操作（update/delete）管理角色或创建者本人 |
| 级联删除 | delete 物理删除，documents/document_chunks 由 FK CASCADE 清理（PG 集成验证） |
| 同名处理 | 同组织范围内重名 → 409 DUPLICATE_NAME |
| SQL NULL 语义 | `allowed_roles` 列 `JSONB(none_as_null=True)`：None → SQL NULL（`null` 表示全员，修复 asyncpg/IS NULL 语义） |
| 兼容 | DEMO_MODE=true 保留内存行为；API path/response schema 未变（新增 request 可选字段） |

### 8.3 边界

- 已实现/已验证：KB CRUD 生产化 + 权限继承 + 级联删除 + 同名处理（PG 集成固化）。
- 未处理：文档管理接口（list_documents/upload/publish/delete_document）的 CRUD 部分仍 Demo（upload 生产链路 Task 20 已闭环）；AI Sales Agent 等新功能不在范围。


---

## 9. Document Management Production 化（Task 22）

> 状态：**Implemented + Tested**（PG 集成 tests/knowledge/test_document_management.py 7 用例，CI backend-pg 纳入）

### 9.1 文档生命周期全链路 DB backed

```
管理员 → GET    /api/v1/admin/kb/{kb_id}/documents            → DB query（JOIN KB 角色+组织过滤）
      → GET    /api/v1/admin/kb/{kb_id}/documents/{doc_id}   → DB query（越权/不存在 → 404）
      → POST   /api/v1/admin/kb/{kb_id}/documents/upload     → Task 20 生产链路（解析→分块→embedding→PG+pgvector）
      → POST   /api/v1/admin/kb/{kb_id}/documents/{doc_id}/publish    → status=published + published_at
      → POST   /api/v1/admin/kb/{kb_id}/documents/{doc_id}/unpublish  → status=draft
      → DELETE /api/v1/admin/kb/{kb_id}/documents/{doc_id}   → DB 物理删除（FK CASCADE 清 chunks/embedding）+ KB 计数回退
```

### 9.2 关键保证

| 项 | 实现 |
|----|------|
| Repository 层 | `repositories/document_repository.py`（SQLAlchemy async，API 层不直接操作 ORM） |
| 权限继承 | Document 可见性 JOIN KnowledgeBase：角色 `allowed_roles IS NULL OR ? role` + 组织 `organization_id IS NULL OR IN accessible_org_ids`（Task 17B/21 同语义） |
| 写权限 | publish/unpublish/delete 仅管理角色或创建者本人（`_can_manage_kb` 复用，越权 403） |
| 级联删除 | delete 物理删除，document_chunks（含 embedding）由 FK `ondelete=CASCADE` 清理，无孤儿数据（PG 集成验证） |
| 计数一致性 | delete 后 KB `document_count`/`total_chunks` 同步回退 |
| 404 vs 403 | 资源不可见（组织外/角色不符）→ 404 不泄露存在性；可见但无写权限 → 403 |
| 兼容 | DEMO_MODE=true 保留内存行为；既有 API path/response schema 不变（新增 detail/unpublish 路由向后兼容） |

### 9.3 边界

- 已实现/已验证：Document list/detail/publish/unpublish/delete 生产化 + 权限继承 + 级联删除 + 计数回退。
- 未处理：文档内容编辑/版本管理（previous_version_id 已有列未闭环）、AI Sales Agent 等新功能。


---

## AI Sales Agent × RAG（Task 27）

- Agent 的 `search_product_knowledge` 工具复用 RAGPipeline（Vector + BM25 + RRF + Product Boundary + Role/Org 权限 + Confidence Gate + Citation）。
- RAG REFUSE → Agent 跳过话术生成（不编造产品条款），拒答状态结构化返回前端；citation 进入最终 agent_complete。
- PG 集成验证：AGENT@A 的 citation 只属于有权 KB（KB-B 角色不符 / KB-C 组织不符不泄漏）。
