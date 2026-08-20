#!/usr/bin/env python3
"""Real AI Performance Layer C Benchmark（RDY 阶段3，opt-in workflow_dispatch）。

在 DEMO_MODE=false + 真实 PostgreSQL/pgvector + Redis + 真实 DashScope/Qwen 环境下，
对三类真实 AI 链路做小规模、可控成本的基准测量（默认每类 3 次，AZB_BENCH_REPEAT 可调）：

  1) Product QA SSE   —— ProductQaService.chat（RAG + 流式生成）
  2) Script Generation —— ScriptService.generate_scripts（RAG 增强话术 + 合规）
  3) Sales Agent GF   —— SalesAgentService.chat（完整工具链，逐事件阶段分解）

记录指标：time-to-first-event (TTFB)、total latency、p50/p95（样本足够时）、
RAG latency、provider 生成 latency、tool 数、token/事件计数、error rate。
不输出：完整 prompt、客户 PII、API key。

结果写 /tmp/real_ai_layer_c.json（原始样本 + 汇总统计），供 workflow artifact 归档。
无 AZB_AI_API_KEY 时打印 NOT_RUN 并以 0 退出（不假装通过）。
"""
import asyncio
import json
import os
import statistics
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.customer import Customer
from app.models.user import User

AGENT_PHONE = os.environ.get("PILOT_AGENT_PHONE", "13800138000")
PILOT_CUSTOMER_PHONE = os.environ.get("PILOT_CUSTOMER_PHONE", "13900000001")
REPEAT = int(os.environ.get("AZB_BENCH_REPEAT", "3"))
OUT_PATH = os.environ.get("BENCH_OUT", "/tmp/real_ai_layer_c.json")

# 确定性查询（Sales Agent 必须用 Pilot synthetic 客户，不用真实客户数据）
QA_QUESTION = "百万医疗险的保障范围包括哪些？理赔流程是怎样的？"
SCRIPT_STYLE = "professional"
SCRIPT_PRODUCT_TYPE = "医疗险"
AGENT_MESSAGE = "客户想了解百万医疗险的保障范围和理赔流程，帮我准备沟通话术"


def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * p
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    return s[f] + (s[c] - s[f]) * (k - f)


def summarize(name: str, samples: list[dict]) -> dict:
    """对一组样本做汇总统计（mean/p50/p95/min/max）。"""
    out = {"name": name, "n": len(samples), "samples": samples}
    for key in ("ttfb_ms", "total_ms"):
        vals = [s.get(key) for s in samples if s.get(key) is not None]
        if vals:
            out[f"{key}_mean"] = round(statistics.mean(vals), 1)
            out[f"{key}_p50"] = round(_pct(vals, 0.50), 1)
            out[f"{key}_p95"] = round(_pct(vals, 0.95), 1)
            out[f"{key}_min"] = round(min(vals), 1)
            out[f"{key}_max"] = round(max(vals), 1)
    return out


async def bench_product_qa(session: AsyncSession, user: User) -> list[dict]:
    from app.ai.service import ProductQaService

    svc = ProductQaService(db=session)
    samples = []
    for i in range(REPEAT):
        events: list[str] = []
        first_t = None
        t0 = time.perf_counter()
        async for ev in svc.chat(
            user=user,
            question=QA_QUESTION,
            conversation_id=str(uuid.uuid4()),
            knowledge_scope="all",
        ):
            if first_t is None:
                first_t = (time.perf_counter() - t0) * 1000
            events.append(ev)
        total = (time.perf_counter() - t0) * 1000
        samples.append({
            "run": i + 1, "ttfb_ms": round(first_t or 0, 1),
            "total_ms": round(total, 1), "events": len(events),
            "error": any('"event": "error"' in e for e in events),
        })
        print(f"  [QA {i+1}/{REPEAT}] ttfb={samples[-1]['ttfb_ms']}ms total={samples[-1]['total_ms']}ms events={len(events)}")
    return samples


async def bench_script_gen(session: AsyncSession, user: User) -> list[dict]:
    from app.services.script_service import ScriptService

    svc = ScriptService(session)
    customer_context = {
        "name": "陈女士", "age": 42, "objection": "想了解保障范围和理赔流程",
        "stage": "needs_analysis", "product_type": SCRIPT_PRODUCT_TYPE,
    }
    samples = []
    for i in range(REPEAT):
        events: list[str] = []
        first_t = None
        t0 = time.perf_counter()
        async for ev in svc.generate_scripts(
            customer_context=customer_context,
            style=SCRIPT_STYLE,
            product_type=SCRIPT_PRODUCT_TYPE,
            user_id=str(user.id),
        ):
            if first_t is None:
                first_t = (time.perf_counter() - t0) * 1000
            events.append(ev)
        total = (time.perf_counter() - t0) * 1000
        n_scripts = sum(1 for e in events if '"event": "style_complete"' in e)
        samples.append({
            "run": i + 1, "ttfb_ms": round(first_t or 0, 1),
            "total_ms": round(total, 1), "events": len(events),
            "scripts": n_scripts,
            "error": any('"event": "error"' in e for e in events),
        })
        print(f"  [SCR {i+1}/{REPEAT}] ttfb={samples[-1]['ttfb_ms']}ms total={samples[-1]['total_ms']}ms scripts={n_scripts}")
    return samples


async def bench_sales_agent(session: AsyncSession, user: User, customer: Customer) -> list[dict]:
    from app.agent.orchestrator import SalesAgentService

    svc = SalesAgentService(db=session)
    samples = []
    for i in range(REPEAT):
        # 逐事件计时 → 阶段分解
        timeline: list[tuple[str, float]] = []  # (event/phase, ts_ms)
        last_ts = 0.0
        t0 = time.perf_counter()
        async for ev in svc.chat(
            user=user,
            customer_id=str(customer.id),
            message=AGENT_MESSAGE,
            product_type=SCRIPT_PRODUCT_TYPE,
            sales_stage="needs_analysis",
            session_id=str(uuid.uuid4()),
            request_id=f"bench-{uuid.uuid4().hex[:8]}",
        ):
            ts = (time.perf_counter() - t0) * 1000
            timeline.append((ev, ts))
            last_ts = ts

        # 解析事件流 → 阶段耗时
        phases = {}
        tool_start_ts: dict[str, float] = {}
        pending: list[str] = []
        comp_latency = None
        total_ms = last_ts
        for ev, ts in timeline:
            try:
                obj = json.loads(ev)
            except Exception:
                continue
            evt = obj.get("event")
            data = obj.get("data") or {}
            if evt == "agent_start":
                phases["agent_start"] = ts
            elif evt == "tool_start":
                tool_start_ts[data.get("tool", "")] = ts
                pending.append(data.get("tool", ""))
            elif evt in ("tool_result", "rag_context", "compliance"):
                if pending:
                    tool = pending.pop()
                    if tool and tool in tool_start_ts:
                        phases[f"tool_{tool}"] = ts - tool_start_ts[tool]
            elif evt == "agent_complete":
                comp_latency = data.get("latency_ms")
                phases["agent_complete"] = ts
                total_ms = ts

        # 阶段分解（ms）：customer_ctx / activity / rag / script / compliance / summarize
        breakdown = {
            "customer_context_ms": round(phases.get("tool_get_customer_context", 0.0), 1),
            "activity_ms": round(phases.get("tool_get_customer_activity", 0.0), 1),
            "rag_ms": round(phases.get("tool_search_product_knowledge", 0.0), 1),
            "script_gen_ms": round(phases.get("tool_generate_sales_script", 0.0), 1),
            "compliance_ms": round(phases.get("tool_check_compliance", 0.0), 1),
            "total_ms": round(total_ms, 1),
            "agent_complete_latency_ms": comp_latency,
            "tool_count": len(tool_start_ts),
            "event_count": len(timeline),
            "error": any('"event": "error"' in ev for ev, _ in timeline),
        }
        samples.append({"run": i + 1, **breakdown})
        print(
            f"  [AGENT {i+1}/{REPEAT}] ctx={breakdown['customer_context_ms']}ms "
            f"activity={breakdown['activity_ms']}ms rag={breakdown['rag_ms']}ms "
            f"script={breakdown['script_gen_ms']}ms compliance={breakdown['compliance_ms']}ms "
            f"total={breakdown['total_ms']}ms tools={breakdown['tool_count']}"
        )
    return samples


async def main() -> int:
    if settings.DEMO_MODE:
        print("real_ai_layer_c: DEMO_MODE=true —— 本 benchmark 仅适用于 Production-like 环境（DEMO_MODE=false）")
        return 1
    if not settings.AI_API_KEY:
        print("real_ai_layer_c: NOT_RUN —— AZB_AI_API_KEY 未配置（真实 AI 不可用，不假装通过）")
        return 0

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    report: dict = {
        "provider": settings.AI_PROVIDER,
        "model": settings.AI_MODEL,
        "embedding_model": settings.AI_EMBEDDING_MODEL,
        "repeat": REPEAT,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results": {},
    }
    try:
        async with Session() as session:
            user = (
                await session.execute(select(User).where(User.phone == AGENT_PHONE))
            ).scalar_one_or_none()
            if user is None:
                print(f"real_ai_layer_c: AGENT {AGENT_PHONE} 不存在（先执行 seed）")
                return 1
            customer = (
                await session.execute(select(Customer).where(Customer.phone == PILOT_CUSTOMER_PHONE))
            ).scalar_one_or_none()
            if customer is None:
                print(f"real_ai_layer_c: Pilot 客户 {PILOT_CUSTOMER_PHONE} 不存在（先执行 seed）")
                return 1

            print(f"=== Real AI Layer C Benchmark（provider={settings.AI_PROVIDER}, model={settings.AI_MODEL}, repeat={REPEAT}）===")
            print("--- 1) Product QA SSE ---")
            qa = await bench_product_qa(session, user)
            print("--- 2) Script Generation ---")
            scr = await bench_script_gen(session, user)
            print("--- 3) Sales Agent GF（27.6s 延迟分解）---")
            ag = await bench_sales_agent(session, user)

            report["results"]["product_qa"] = summarize("product_qa", qa)
            report["results"]["script_generation"] = summarize("script_generation", scr)
            report["results"]["sales_agent"] = summarize("sales_agent", ag)

            # 27.6s 分解汇总：各阶段 p50（样本足够时）
            if len(ag) >= 2:
                for stage in ("customer_context_ms", "activity_ms", "rag_ms", "script_gen_ms", "compliance_ms"):
                    vals = [s.get(stage) for s in ag if s.get(stage) is not None]
                    if vals:
                        report["results"]["sales_agent"][f"{stage}_p50"] = round(_pct(vals, 0.50), 1)
            report["results"]["sales_agent"]["total_ms_p50"] = round(
                _pct([s["total_ms"] for s in ag], 0.50), 1) if ag else 0.0
            report["results"]["sales_agent"]["total_ms_p95"] = round(
                _pct([s["total_ms"] for s in ag], 0.95), 1) if ag else 0.0

            os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
            with open(OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"=== Benchmark 完成 → {OUT_PATH} ===")
            print(f"QA total p50={report['results']['product_qa'].get('total_ms_p50')}ms; "
                  f"SCR total p50={report['results']['script_generation'].get('total_ms_p50')}ms; "
                  f"AGENT total p50={report['results']['sales_agent'].get('total_ms_p50')}ms")
            return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
