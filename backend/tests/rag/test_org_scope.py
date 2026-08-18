"""Task 17B — RAG 组织范围隔离（KnowledgeBase.organization_id）测试。

覆盖用例（测试矩阵 D/E/F/G）：
- D: KB.org=A, User.org=A → 结果非空
- E: KB.org=A, User.org=B → 结果空
- F: Branch A 下属 Team A1/A2，BRANCH_ADMIN 检索 → 仅命中 A 分支子树
- G: role 命中但 org 不命中 → 结果空（联合权限）

双路径：
- Demo：DemoRetriever（chunk 携带 kb_org_id）
- SQL：Retriever._permission_conditions 组织条件编译断言（postgresql 方言）
- 组织范围来源：DataPermissionChecker.filter_accessible_org_ids（复用，不重造）
"""
import uuid

import pytest

from app.core.authorization import DataPermissionChecker
from app.models.user import User
from app.rag.retriever import DemoRetriever, Retriever

ORG_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ORG_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
BRANCH_A = "10000000-0000-0000-0000-00000000000a"
TEAM_A1 = "10000000-0000-0000-0000-0000000000a1"
TEAM_A2 = "10000000-0000-0000-0000-0000000000a2"
ORG_OTHER = "cccccccc-cccc-cccc-cccc-cccccccccccc"


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
# Demo 路径（用例 D / E / G）
# ==================================================================

class TestOrgScopeDemo:
    async def test_rag_perm_d_same_org_hits(self):
        """D: KB.org=A, User.org=A → 结果非空。"""
        r = _demo_retriever([
            _chunk("A 机构专属产品方案 保障范围", kb_roles=["AGENT"], org_id=ORG_A),
        ])
        results = await r.search("保障范围", user_roles=["AGENT"], org_id=ORG_A)
        assert len(results) >= 1

    async def test_rag_perm_e_cross_org_blocked(self):
        """E: KB.org=A, User.org=B → 结果空。"""
        r = _demo_retriever([
            _chunk("A 机构专属产品方案 保障范围", kb_roles=["AGENT"], org_id=ORG_A),
        ])
        results = await r.search("保障范围", user_roles=["AGENT"], org_id=ORG_B)
        assert results == []

    async def test_rag_perm_g_role_ok_org_no(self):
        """G: role 命中但 org 不命中 → 结果空（联合权限）。"""
        r = _demo_retriever([
            _chunk("A 机构内部资料 佣金政策", kb_roles=["AGENT"], org_id=ORG_A),
        ])
        results = await r.search(
            "佣金政策", user_roles=["AGENT"],
            accessible_org_ids=[ORG_B],
        )
        assert results == []

    async def test_rag_perm_d_accessible_org_ids_multi(self):
        """D(变体): accessible_org_ids 多组织集合 → 命中集合内组织。"""
        r = _demo_retriever([
            _chunk("A 机构资料 核保规则", kb_roles=["AGENT"], org_id=ORG_A),
            _chunk("B 机构资料 核保规则", kb_roles=["AGENT"], org_id=ORG_B),
        ])
        results = await r.search(
            "核保规则", user_roles=["AGENT"], accessible_org_ids=[ORG_A, ORG_B],
        )
        assert len(results) == 2

    async def test_rag_perm_shared_kb_visible_across_org(self):
        """org=NULL（未限定组织的共享知识库）→ 各组织可见（仍受角色约束）。"""
        r = _demo_retriever([
            _chunk("共享产品手册 保障范围", kb_roles=["AGENT"], org_id=None),
        ])
        results = await r.search("保障范围", user_roles=["AGENT"], org_id=ORG_B)
        assert len(results) >= 1


# ==================================================================
# 用例 F：BRANCH_ADMIN 组织树（DataPermissionChecker 复用）
# ==================================================================

class TestBranchAdminOrgTree:
    @staticmethod
    def _make_user(phone: str, role_code: str, org_id: str) -> User:
        from app.models.role import Role

        user = User(
            id=uuid.uuid4(),
            phone=phone,
            name="测试用户",
            password_hash=None,
            role_id=uuid.uuid4(),
            organization_id=uuid.UUID(org_id),
            status="active",
            demo_mode=False,
        )
        # role_code 依赖 role 关系（lazy="joined"），内存对象需手动挂载
        user.role = Role(
            id=uuid.uuid4(),
            code=role_code,
            name=f"角色{role_code}",
            level=1,
        )
        return user

    async def test_rag_perm_f_branch_admin_only_branch_subtree(self, monkeypatch):
        """F: Branch A 下属 Team A1/A2，BRANCH_ADMIN 检索 → 仅命中 A 分支子树。"""
        user = self._make_user("13900000000", "BRANCH_ADMIN", BRANCH_A)
        # 组织树收集：正式模式走 org.children 递归，此处 monkeypatch 返回子树
        monkeypatch.setattr(
            DataPermissionChecker, "_collect_child_org_ids",
            lambda self, root: [str(root)] if root != BRANCH_A else [BRANCH_A, TEAM_A1, TEAM_A2],
        )
        checker = DataPermissionChecker(user)
        accessible = checker.filter_accessible_org_ids()
        assert set(accessible) == {BRANCH_A, TEAM_A1, TEAM_A2}

        r = _demo_retriever([
            _chunk("分支A产品资料 保障范围", kb_roles=["BRANCH_ADMIN"], org_id=BRANCH_A),
            _chunk("团队A1资料 客户策略", kb_roles=["BRANCH_ADMIN"], org_id=TEAM_A1),
            _chunk("团队A2资料 客户策略", kb_roles=["BRANCH_ADMIN"], org_id=TEAM_A2),
            _chunk("其他分支B资料 内部费率", kb_roles=["BRANCH_ADMIN"], org_id=ORG_OTHER),
        ])
        results = await r.search(
            "客户策略 保障范围", user_roles=["BRANCH_ADMIN"], accessible_org_ids=accessible,
        )
        hit_orgs = {res.metadata.get("kb_org_id") for res in results}
        assert hit_orgs <= {BRANCH_A, TEAM_A1, TEAM_A2}, f"仅命中分支子树: {hit_orgs}"
        assert ORG_OTHER not in hit_orgs

    async def test_rag_perm_f_system_admin_all_orgs(self):
        """SYSTEM_ADMIN：accessible_org_ids=["__ALL__"] → 跨组织全量可见。"""
        user = self._make_user("13900000001", "SYSTEM_ADMIN", ORG_A)
        checker = DataPermissionChecker(user)
        accessible = checker.filter_accessible_org_ids()
        assert accessible == ["__ALL__"]

        r = _demo_retriever([
            _chunk("A 机构资料 核保规则", kb_roles=["AGENT"], org_id=ORG_A),
            _chunk("B 机构资料 核保规则", kb_roles=["AGENT"], org_id=ORG_B),
        ])
        results = await r.search(
            "核保规则", user_roles=["AGENT"], accessible_org_ids=accessible,
        )
        assert len(results) == 2


# ==================================================================
# SQL 组织条件编译断言（不依赖真实 PG）
# ==================================================================

class TestOrgConditionSql:
    def _compile(self, conditions):
        from sqlalchemy.dialects import postgresql
        from sqlalchemy import select
        from app.models.knowledge import KnowledgeBase
        stmt = select(KnowledgeBase.id).where(*conditions) if conditions else select(KnowledgeBase.id)
        return str(stmt.compile(dialect=postgresql.dialect()))

    def test_rag_perm_org_condition_in_list(self):
        conds = Retriever._permission_conditions(None, [ORG_A, ORG_B])
        sql = self._compile(conds)
        # 共享（NULL）或命中可访问集合
        assert "organization_id IS NULL" in sql
        assert "IN" in sql.upper()

    def test_rag_perm_org_all_skips_condition(self):
        conds = Retriever._permission_conditions(None, ["__ALL__"])
        assert conds == []

    def test_rag_perm_org_fallback_single_org_id(self):
        conds = Retriever._permission_conditions(None, None, org_id=ORG_A)
        sql = self._compile(conds)
        assert "organization_id IS NULL" in sql

    def test_rag_perm_combined_role_and_org(self):
        conds = Retriever._permission_conditions(["AGENT"], [ORG_A])
        sql = self._compile(conds)
        assert "allowed_roles IS NULL" in sql
        assert "allowed_roles ?" in sql
        assert "organization_id IS NULL" in sql
