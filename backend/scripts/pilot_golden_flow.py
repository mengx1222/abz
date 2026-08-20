#!/usr/bin/env python3
"""Internal Pilot Golden Flow — 服务级真实验证（ULTIMATE Pilot Validation）。

在真实 PG16+pgvector + Redis + 当前 Pilot seed + 真实 AI Provider（opt-in）环境下，
验证一条 AGENT 黄金链路的数据与权限真正连续：

A. Pilot seed 完整性（真实 DB 查询：AGENT/3 客户 assigned/互动/跟进/KB/文档/chunks/embeddings/训练场景）
B. Customer 权限（P0-1 assigned_to 同源：本人可见/他人不可见/跨组织拒绝/列表仅本人）
C. RAG 检索（知识库命中 + Citation + 无依据问题 REFUSE）
D. AI Sales Agent（真实执行：agent_start/rag_context/citation/compliance/agent_complete）
E. Training（真实会话：start → 2 轮消息 → complete 评分）
F. Growth 连续性（同用户训练结果：training_count/total_exp/ability_scores）

用法（backend 目录）:
    python -m scripts.pilot_golden_flow

环境变量（AZB_ 前缀）由 workflow 注入；AI Provider 非 mock 时记录真实 provider/latency，
mock 时相关步骤标记 NOT_RUN（不假装通过）。输出 JSON 到 stdout + /tmp/pilot_golden_flow.json。
"""
import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.authorization import DataPermissionChecker
from app.models.customer import Customer, CustomerFollowup, CustomerInteraction
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.models.organization import Organization
from app.models.role import Role
from app.models.training import TrainingScenario
from app.models.user import User
from app.rag.pipeline import RAGPipeline
from app.rag.safety import should_refuse_answer

AGENT_PHONE = os.environ.get("PILOT_AGENT_PHONE", "13800138000")
KB_NAME = "E2E产品知识库"
PILOT_PHONES = ["13900000001", "13900000002", "13900000003"]

results: list[dict] = []


def record(name: str, ok: bool, detail: str, extra: dict | None = None):
    results.append({
        "name": name,
        "status": "PASS" if ok else "FAIL",
        "detail": detail,
        **(extra or {}),
    })
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


# ------------------------------------------------------------------
# A. Pilot seed 完整性
# ------------------------------------------------------------------

async def verify_seed(session: AsyncSession) -> None:
    agent = (
        await session.execute(select(User).where(User.phone == AGENT_PHONE))
    ).scalar_one_or_none()
    record("seed.agent_user", agent is not None,
           f"AGENT {AGENT_PHONE} 存在" if agent else f"AGENT {AGENT_PHONE} 缺失")
    if agent is None:
        return

    role = (await session.execute(select(Role).where(Role.id == agent.role_id))).scalar_one()
    org = (await session.execute(select(Organization).where(Organization.id == agent.organization_id))).scalar_one()
    record("seed.agent_role_org",
           role.code == "AGENT" and org is not None,
           f"role={role.code}, org={org.name}")

    # 3 pilot customers assigned to agent
    custs = (
        await session.execute(
            select(Customer).where(Customer.phone.in_(PILOT_PHONES))
        )
    ).scalars().all()
    by_phone = {c.phone: c for c in custs}
    record("seed.pilot_customers",
           len(by_phone) == len(PILOT_PHONES) and all(
               by_phone[p] is not None and str(by_phone[p].assigned_to) == str(agent.id)
               and str(by_phone[p].organization_id) == str(agent.organization_id)
               for p in PILOT_PHONES
           ),
           f"customers={len(by_phone)}/{len(PILOT_PHONES)}，全部 assigned_to=AGENT 且同组织")

    # interactions + followups
    for phone in PILOT_PHONES:
        c = by_phone.get(phone)
        if c is None:
            continue
        icount = (await session.execute(
            select(func.count()).select_from(CustomerInteraction).where(CustomerInteraction.customer_id == c.id)
        )).scalar_one()
        fcount = (await session.execute(
            select(func.count()).select_from(CustomerFollowup).where(CustomerFollowup.customer_id == c.id)
        )).scalar_one()
        record(f"seed.customer_{phone}.interaction_followup",
               icount >= 1 and fcount >= 1,
               f"interactions={icount}, followups={fcount}")

    # KB / docs / chunks / embeddings
    kb = (
        await session.execute(select(KnowledgeBase).where(KnowledgeBase.name == KB_NAME))
    ).scalar_one_or_none()
    record("seed.knowledge_base", kb is not None, f"KB '{KB_NAME}' 存在" if kb else "KB 缺失")
    if kb is None:
        return
    doc_count = (await session.execute(
        select(func.count()).select_from(Document).where(Document.knowledge_base_id == kb.id)
    )).scalar_one()
    chunks = (await session.execute(
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.knowledge_base_id == kb.id)
    )).scalars().all()
    emb_dims = {len(c.embedding) for c in chunks if c.embedding}
    record("seed.kb_docs_chunks_embeddings",
           doc_count >= 2 and len(chunks) >= 6 and emb_dims == {1536},
           f"docs={doc_count}, chunks={len(chunks)}, embedding_dims={emb_dims or 'EMPTY'}")

    scenario_count = (await session.execute(
        select(func.count()).select_from(TrainingScenario)
    )).scalar_one()
    record("seed.training_scenarios", scenario_count >= 1, f"scenarios={scenario_count}")


# ------------------------------------------------------------------
# B. Customer 权限（P0-1 同源）
# ------------------------------------------------------------------

async def verify_permission(session: AsyncSession, agent: User) -> None:
    checker = DataPermissionChecker(agent)
    own = (await session.execute(
        select(Customer).where(Customer.phone == PILOT_PHONES[0])
    )).scalar_one()
    other_agent_id = uuid.uuid4()

    record("perm.own_assigned_ok",
           checker.can_access_customer(str(own.organization_id), str(own.assigned_to)),
           "AGENT 可见本人 assigned 客户")
    record("perm.other_assigned_denied",
           not checker.can_access_customer(str(own.organization_id), str(other_agent_id)),
           "AGENT 不可见他人 assigned 客户")
    record("perm.cross_org_denied",
           not checker.can_access_customer(str(uuid.uuid4()), str(agent.id)),
           "AGENT 跨组织不可见")

    from app.services.customer_service import CustomerService
    svc = CustomerService(session)
    items, total = await svc.list_customers(current_user=agent)
    own_ids = {str(own.id)}
    items_ids = {str(i["id"]) for i in items}
    record("perm.list_only_own",
           total >= 1 and items_ids <= {str(c.id) for c in (await session.execute(
               select(Customer).where(Customer.assigned_to == agent.id)
           )).scalars().all()},
           f"list total={total}（列表过滤与详情同源：仅本人 assigned）")


# ------------------------------------------------------------------
# C. RAG 检索 + Citation + REFUSE
# ------------------------------------------------------------------

async def verify_rag(session: AsyncSession, agent: User) -> None:
    pipeline = RAGPipeline(db=session)
    checker = DataPermissionChecker(agent)
    org_id = str(agent.organization_id)
    roles = [agent.role_code] if hasattr(agent, "role_code") else None

    # 1) 有依据问题 → hit>0
    t0 = time.perf_counter()
    results_q, context = await pipeline.query(
        question="百万医疗险的保障范围包括哪些？理赔流程是怎样的？",
        top_k=8,
        user_roles=roles,
        org_id=org_id,
        accessible_org_ids=checker.filter_accessible_org_ids(),
    )
    latency = round((time.perf_counter() - t0) * 1000, 1)
    refuse, top_score, count = should_refuse_answer(results_q)
    record("rag.hit",
           len(results_q) > 0 and not refuse,
           f"results={len(results_q)}, top_score={top_score:.3f}, latency={latency}ms, rag_status={'REFUSE' if refuse else 'ALLOW/REVIEW'}")
    if results_q:
        top = results_q[0]
        record("rag.citation_metadata",
               bool(top.document_title) and bool(top.metadata.get("heading", "") or top.metadata.get("section", "")),
               f"citation: title={top.document_title!r}, section={top.metadata.get('section', '')!r}")

    # 2) 无依据问题 → REFUSE（不编造产品条款）
    results_n, _ = await pipeline.query(
        question="如何判断一颗行星上是否存在液态水？",
        top_k=8,
        user_roles=roles,
        org_id=org_id,
        accessible_org_ids=checker.filter_accessible_org_ids(),
    )
    refuse_n, top_score_n, _ = should_refuse_answer(results_n)
    record("rag.refuse_no_hallucination",
           refuse_n or len(results_n) == 0,
           f"results={len(results_n)}, refuse={refuse_n}, top_score={top_score_n:.3f}（无依据不编造）")


# ------------------------------------------------------------------
# D. AI Sales Agent 真实执行
# ------------------------------------------------------------------

async def verify_agent(session: AsyncSession, agent: User) -> None:
    from app.agent.orchestrator import SalesAgentService

    customer = (await session.execute(
        select(Customer).where(Customer.phone == PILOT_PHONES[0])
    )).scalar_one()

    provider = settings.AI_PROVIDER
    if provider == "mock":
        record("agent.real_ai", False,
               f"AI_PROVIDER={provider} —— 真实 AI NOT RUN（未配置 Key）；Agent 逻辑仍执行（mock provider）")
    else:
        record("agent.real_ai", True, f"AI_PROVIDER={provider}（真实 AI）")

    svc = SalesAgentService(db=session)
    events: list[dict] = []
    t0 = time.perf_counter()
    async for event_json in svc.chat(
        user=agent,
        customer_id=str(customer.id),
        message="客户想了解百万医疗险的保障范围和理赔流程，帮我准备沟通话术",
        product_type="医疗险",
        sales_stage="needs_analysis",
        session_id=str(uuid.uuid4()),
        request_id=f"pilot-{uuid.uuid4().hex[:8]}",
    ):
        import json as _json
        try:
            events.append(_json.loads(event_json))
        except Exception:
            events.append({"event": "raw", "data": str(event_json)[:100]})
    latency = round((time.perf_counter() - t0) * 1000, 1)

    kinds = {e.get("event") for e in events}
    rag_ctx = next((e for e in events if e.get("event") == "rag_context"), None)
    compl_ev = next((e for e in events if e.get("event") == "compliance"), None)
    complete = next((e for e in events if e.get("event") == "agent_complete"), None)

    record("agent.flow_events",
           {"agent_start", "agent_complete"}.issubset(kinds),
           f"events={sorted(kinds)}, latency={latency}ms")
    rag_status = (rag_ctx or {}).get("data", {}).get("status", "?") if rag_ctx else "?"
    citations = (rag_ctx or {}).get("data", {}).get("citations") or [] if rag_ctx else []
    record("agent.rag_context",
           rag_ctx is not None and rag_status in ("ALLOW", "REVIEW"),
           f"rag_status={rag_status}, sources_count={(rag_ctx or {}).get('data', {}).get('sources_count')}")
    # Citation 内嵌于 rag_context.data.citations（无独立 citation 事件）
    record("agent.citation",
           len(citations) > 0 and bool(citations[0].get("document_title")),
           f"citations={len(citations)}, first_title={citations[0].get('document_title') if citations else '?'}")
    record("agent.compliance",
           compl_ev is not None and (compl_ev.get("data") or {}).get("status") in ("GREEN", "YELLOW", "RED"),
           f"compliance={(compl_ev or {}).get('data', {}).get('status', '?')}")
    status = (complete or {}).get("data", {}).get("status") if complete else "?"
    record("agent.complete",
           complete is not None and status == "completed",
           f"agent_complete.status={status}")


# ------------------------------------------------------------------
# E. Training 真实执行
# ------------------------------------------------------------------

async def verify_training(session: AsyncSession, agent: User) -> None:
    from app.services.training_service import TrainingService

    svc = TrainingService(session)
    scenarios = await svc.get_scenarios()
    if not scenarios:
        record("training.start", False, "无训练场景")
        return
    scenario_id = scenarios[0]["id"]

    started = await svc.start_session(str(agent.id), str(scenario_id))
    session_id = started.get("id") or started.get("session_id")
    record("training.start", bool(session_id), f"session={session_id}")

    if not session_id:
        return
    for i, msg in enumerate([
        "您好，我了解您对保费有些顾虑，能说说主要担心什么吗？",
        "我理解您的想法，保障是应对风险的关键，我们可以看看更合适的方案。",
    ]):
        got = False
        async for _ev in svc.send_message(str(session_id), str(agent.id), msg):
            got = True
        record(f"training.round{i+1}", got, f"round{i+1} 消息已处理")

    score_found = False
    async for ev in svc.complete_session(str(session_id), str(agent.id)):
        import json as _json
        try:
            d = _json.loads(ev)
        except Exception:
            d = {"event": "raw"}
        if d.get("event") in ("score_data", "scoring_complete", "scoring_start"):
            score_found = True
    record("training.complete_score", score_found, "评分事件已生成" if score_found else "评分事件缺失")


# ------------------------------------------------------------------
# F. Growth 连续性
# ------------------------------------------------------------------

async def verify_growth(session: AsyncSession, agent: User) -> None:
    from app.services.growth_service import GrowthService

    svc = GrowthService(session)
    overview = await svc.get_overview(agent.id)
    # GrowthOverview 无 training_count 字段：用 total_exp（1 次完成训练 ×10）+ ability_scores 证明连续性
    total_exp = getattr(overview, "total_exp", None) or 0
    abilities = getattr(overview, "ability_scores", None) or []
    record("growth.continuity",
           total_exp >= 10 and len(abilities) > 0,
           f"total_exp={total_exp}, ability_scores={len(abilities)}（同用户训练结果连续）")


# ------------------------------------------------------------------

async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        agent = (
            await session.execute(select(User).where(User.phone == AGENT_PHONE))
        ).scalar_one_or_none()

        await verify_seed(session)
        if agent is not None:
            await verify_permission(session, agent)
            await verify_rag(session, agent)
            await verify_agent(session, agent)
            await verify_training(session, agent)
            await verify_growth(session, agent)

    await engine.dispose()

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ai_provider": settings.AI_PROVIDER,
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "results": results,
    }
    print("\n===== PILOT GOLDEN FLOW SUMMARY =====")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    with open("/tmp/pilot_golden_flow.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    if failed:
        raise SystemExit(f"PILOT GOLDEN FLOW FAILED: {failed} checks failed")


if __name__ == "__main__":
    asyncio.run(main())
