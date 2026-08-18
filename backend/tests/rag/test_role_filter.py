"""Task 17B — RAG 角色权限过滤（KnowledgeBase.allowed_roles）测试。

覆盖用例（测试矩阵 A/B/C）：
- A: KB.allowed_roles=["AGENT"]，AGENT 检索 → 结果非空
- B: KB.allowed_roles=["HQ_ADMIN"]，AGENT 检索 → 结果空（citation 亦空，见 test_citation_leak）
- C: KB.allowed_roles=NULL（全员），AGENT 检索 → 结果非空，但仍受组织范围约束（联合见 test_org_scope）

双路径：
- Demo：DemoRetriever（chunk 携带 kb_allowed_roles）
- SQL：Retriever._permission_conditions 编译断言（postgresql 方言，不依赖真实 PG）
- 二次校验：Retriever._filter_by_permission 单元测试（纵深防御层）
"""
import uuid

import pytest

from app.rag.retriever import DemoRetriever, Retriever, SearchResult

ORG_A = "11111111-1111-1111-1111-111111111111"


def _chunk(content: str, *, kb_id: str = "kb-1", kb_roles=None, org_id: str | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "content": content,
        "document_title": "测试文档",
        "heading": "保障范围",
        "knowledge_base_id": kb_id,
        "document_id": str(uuid.uuid4()),
        "kb_allowed_roles": kb_roles,
        "kb_org_id": org_id,
    }


def _demo_retriever(chunks: list[dict]) -> DemoRetriever:
    r = DemoRetriever()
    r.add_chunks(chunks)
    return r


# ==================================================================
# Demo 路径（用例 A / B / C）
# ==================================================================

class TestRoleFilterDemo:
    async def test_rag_perm_a_agent_hits_agent_kb(self):
        """A: allowed_roles=["AGENT"]，AGENT 检索 → 结果非空。"""
        r = _demo_retriever([_chunk("百万医疗险 保障范围 600万", kb_roles=["AGENT"])])
        results = await r.search("百万医疗险", user_roles=["AGENT"], org_id=ORG_A)
        assert len(results) >= 1

    async def test_rag_perm_b_agent_blocked_from_hq_kb(self):
        """B: allowed_roles=["HQ_ADMIN"]，AGENT 检索 → 结果空。"""
        r = _demo_retriever([_chunk("总部内部经营数据 保费构成", kb_roles=["HQ_ADMIN"])])
        results = await r.search("保费构成", user_roles=["AGENT"], org_id=ORG_A)
        assert results == []

    async def test_rag_perm_b_hq_admin_hits_hq_kb(self):
        """B(镜像): allowed_roles=["HQ_ADMIN"]，HQ_ADMIN 检索 → 结果非空（角色允许）。"""
        r = _demo_retriever([_chunk("总部内部经营数据 保费构成", kb_roles=["HQ_ADMIN"])])
        results = await r.search("保费构成", user_roles=["HQ_ADMIN"], org_id=ORG_A)
        assert len(results) >= 1

    async def test_rag_perm_c_null_roles_all_visible(self):
        """C: allowed_roles=NULL，AGENT 检索 → 结果非空（全员可见，仍受 org 约束）。"""
        r = _demo_retriever([_chunk("公开产品手册 保障范围", kb_roles=None)])
        results = await r.search("保障范围", user_roles=["AGENT"], org_id=ORG_A)
        assert len(results) >= 1

    async def test_rag_perm_c_null_roles_still_org_bound(self):
        """C(联合): allowed_roles=NULL 但不能绕过 org 范围——其他组织不可见。"""
        r = _demo_retriever([_chunk("公开产品手册 保障范围", kb_roles=None, org_id=ORG_A)])
        results = await r.search(
            "保障范围", user_roles=["AGENT"],
            accessible_org_ids=["22222222-2222-2222-2222-222222222222"],
        )
        assert results == []

    async def test_rag_perm_empty_roles_rejects_all(self):
        """调用方无法确认用户上下文时 user_roles=[] → 全拒（不降级）。"""
        r = _demo_retriever([_chunk("百万医疗险 保障范围", kb_roles=None)])
        results = await r.search("百万医疗险", user_roles=[], org_id=ORG_A)
        assert results == []

    async def test_rag_perm_no_roles_no_filter(self):
        """user_roles=None（未提供权限上下文，兼容既有调用）→ 不限制角色。"""
        r = _demo_retriever([_chunk("百万医疗险 保障范围", kb_roles=["HQ_ADMIN"])])
        results = await r.search("百万医疗险")
        assert len(results) >= 1


# ==================================================================
# SQL 条件编译断言（不依赖真实 PG，验证 WHERE 层角色条件）
# ==================================================================

class TestPermissionConditionsSql:
    def _compile(self, conditions):
        from sqlalchemy.dialects import postgresql
        from sqlalchemy import select, text as sa_text
        # 以 knowledge_bases 为 FROM，把条件编译进 WHERE，验证 SQL 文本
        from app.models.knowledge import KnowledgeBase
        stmt = select(KnowledgeBase.id).where(*conditions) if conditions else select(KnowledgeBase.id)
        return str(stmt.compile(dialect=postgresql.dialect()))

    def test_rag_perm_role_condition_contains_null_and_exists(self):
        conds = Retriever._permission_conditions(["AGENT"], None)
        sql = self._compile(conds)
        # allowed_roles IS NULL（全员）或 jsonb 存在操作符 ?
        assert "allowed_roles IS NULL" in sql
        assert "allowed_roles ?" in sql

    def test_rag_perm_role_condition_multiple_roles(self):
        conds = Retriever._permission_conditions(["AGENT", "TEAM_LEADER"], None)
        sql = self._compile(conds)
        assert sql.count("?") >= 2

    def test_rag_perm_empty_roles_false_condition(self):
        conds = Retriever._permission_conditions([], None)
        sql = self._compile(conds)
        assert "false" in sql.lower()

    def test_rag_perm_null_roles_no_condition(self):
        conds = Retriever._permission_conditions(None, None)
        assert conds == []


# ==================================================================
# 二次校验（_filter_by_permission 纵深防御层）
# ==================================================================

class TestSecondaryFilter:
    def _result(self, content: str, kb_roles=None, kb_org: str | None = None) -> SearchResult:
        metadata = {}
        if kb_roles is not None:
            metadata["kb_allowed_roles"] = kb_roles
        if kb_org is not None:
            metadata["kb_org_id"] = kb_org
        return SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            document_title="测试",
            knowledge_base_id="kb-1",
            content=content,
            score=0.8,
            metadata=metadata,
        )

    def test_rag_perm_secondary_allows_authorized(self):
        results = [self._result("内容A", kb_roles=["AGENT"])]
        out = Retriever._filter_by_permission(results, ["AGENT"])
        assert len(out) == 1

    def test_rag_perm_secondary_blocks_unauthorized(self):
        results = [self._result("内容A", kb_roles=["HQ_ADMIN"])]
        out = Retriever._filter_by_permission(results, ["AGENT"])
        assert out == []

    def test_rag_perm_secondary_null_roles_allowed(self):
        results = [self._result("内容A", kb_roles=None)]
        out = Retriever._filter_by_permission(results, ["AGENT"])
        assert len(out) == 1

    def test_rag_perm_secondary_empty_roles_rejects_all(self):
        results = [self._result("内容A", kb_roles=None)]
        out = Retriever._filter_by_permission(results, [])
        assert out == []

    def test_rag_perm_secondary_org_boundary(self):
        results = [self._result("内容A", kb_roles=["AGENT"], kb_org=ORG_A)]
        # 可访问集合不含 ORG_A → 拦截
        out = Retriever._filter_by_permission(
            results, ["AGENT"], ["22222222-2222-2222-2222-222222222222"],
        )
        assert out == []
        # __ALL__ → 放行
        out_all = Retriever._filter_by_permission(results, ["AGENT"], ["__ALL__"])
        assert len(out_all) == 1
