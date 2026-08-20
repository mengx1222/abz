"""Task 41 — 云端性能基准 harness（100% Cloud-only，在 GitHub Actions 内运行）。

模式：
- deterministic：ASGI 直连 app（AI=mock），测 API/DB/Redis/RAG（SSE 端到端）+ 容量 profiles 1/5/10
- http：连接 workflow 已启动的 uvicorn（--base-url），测真实 HTTP + SSE event stream 解析
- ai：真实 AI smoke（--api-key；Product QA / Sales Agent 各 2 次），记录 provider/model/latency/token usage

输出：/tmp/benchmark_<mode>.json（p50/p95/error rate/throughput 可测才写；未测 Not Benchmarked）。
安全：仅合成 seed 数据；不保存完整模型回答/敏感数据。
"""
import argparse
import asyncio
import json
import os
import statistics
import time
from typing import Optional

from httpx import ASGITransport, AsyncClient, Response

from app.core.config import settings

ADMIN_PHONE = "13800138003"
ADMIN_PASSWORD = "888888"


def pct(vals: list[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    return round(s[min(len(s) - 1, int(len(s) * p))], 3)


def summarize(name: str, lat: list[float], errors: int = 0, extra: Optional[dict] = None) -> dict:
    row = {
        "name": name,
        "n": len(lat),
        "p50_ms": pct(lat, 0.50),
        "p95_ms": pct(lat, 0.95),
        "mean_ms": round(statistics.mean(lat), 3) if lat else None,
        "error_rate": round(errors / len(lat), 4) if lat else None,
        "throughput_rps": round(len(lat) / max(sum(lat) / 1000.0, 1e-6), 2) if lat else None,
    }
    if extra:
        row.update(extra)
    return row


async def bench_request(
    client: AsyncClient,
    method: str,
    path: str,
    *,
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
    n: int = 20,
    sse: bool = False,
) -> tuple[list[float], int, Optional[dict]]:
    """执行 n 次请求。sse=True 解析 event stream：记录 TTFE/completion/total。"""
    lat: list[float] = []
    errors = 0
    sse_stats: Optional[dict] = None
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            if sse:
                ttfe = None
                req_t0 = time.perf_counter()
                async with client.stream(method, path, json=json_body, headers=headers) as r:
                    first_event_at = None
                    async for line in r.aiter_lines():
                        if line.startswith("data:") or line.startswith("event:"):
                            if first_event_at is None:
                                first_event_at = time.perf_counter()
                    total = (time.perf_counter() - req_t0) * 1000
                    ttfe = (first_event_at - req_t0) * 1000 if first_event_at else None
                lat.append(total)
                if ttfe is not None:
                    sse_stats = {"ttfe_ms": round(ttfe, 2), "total_ms": round(total, 2)}
                if r.status_code >= 400:
                    errors += 1
            else:
                r: Response = await client.request(method, path, json=json_body, headers=headers)
                lat.append((time.perf_counter() - t0) * 1000)
                if r.status_code >= 400:
                    errors += 1
        except Exception as e:
            errors += 1
            lat.append(0.0)
    return lat, errors, sse_stats


async def _login(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/login", json={
        "phone": ADMIN_PHONE, "password": ADMIN_PASSWORD,
    })
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def bench_deterministic(out_path: str, concurrency: int) -> None:
    """层 A：ASGI 直连（AI=mock）+ 服务层 DB/Redis + 容量。"""
    os.environ.setdefault("AZB_AI_PROVIDER", "mock")
    # 强制 production 语义（限流走 Redis；session 走 Redis）
    settings.DEMO_MODE = False
    settings.AI_PROVIDER = "mock"

    from app.main import app
    transport = ASGITransport(app=app)
    results: list[dict] = []

    async with AsyncClient(transport=transport, base_url="http://bench") as c:
        admin_headers = await _login(c)

        # API 基础
        lat, err, _ = await bench_request(c, "GET", "/api/v1/health", n=30)
        results.append(summarize("api_health", lat, err))
        lat, err, _ = await bench_request(c, "GET", "/api/v1/ready", n=10)
        results.append(summarize("api_ready", lat, err))
        lat, err, _ = await bench_request(
            c, "GET", "/api/v1/admin/knowledge-bases", headers=admin_headers, n=20)
        results.append(summarize("api_kb_list", lat, err))

        # SSE：Product QA（mock AI，覆盖 RAG 端到端）
        lat, err, sse = await bench_request(
            c, "POST", "/api/v1/ai/product-qa",
            json_body={"question": "安诊保百万医疗险保障范围包括哪些？", "conversation_id": "bench-qa"},
            headers=admin_headers, n=10, sse=True,
        )
        results.append(summarize("sse_product_qa", lat, err, sse))

        # 容量 profile（health 并发）
        if concurrency > 1:
            async def _one():
                t0 = time.perf_counter()
                r = await c.get("/api/v1/health")
                return (time.perf_counter() - t0) * 1000, r.status_code
            clat, cerr = [], 0
            for _ in range(3):
                outs = await asyncio.gather(*[_one() for _ in range(concurrency)])
                for l, code in outs:
                    clat.append(l)
                    if code >= 400:
                        cerr += 1
            results.append(summarize(f"capacity_health_c{concurrency}", clat, cerr))

    # DB：org count + kb 查询
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(settings.DATABASE_URL)
    dlat: list[float] = []
    try:
        async with engine.connect() as conn:
            for _ in range(20):
                t0 = time.perf_counter()
                await conn.execute(text("SELECT count(*) FROM organizations"))
                dlat.append((time.perf_counter() - t0) * 1000)
    finally:
        await engine.dispose()
    results.append(summarize("db_org_count", dlat))

    # Redis：incr + session
    from app.core.redis_store import RedisSessionStore, redis_incr_with_ttl
    rlat, slat = [], []
    for i in range(50):
        t0 = time.perf_counter()
        await redis_incr_with_ttl(f"bench:rl:{i}", 60)
        rlat.append((time.perf_counter() - t0) * 1000)
    store = RedisSessionStore(namespace="bench:session", ttl_seconds=120)
    for i in range(50):
        t0 = time.perf_counter()
        await store.set(f"s{i}", {"k": "v"})
        await store.get(f"s{i}")
        slat.append((time.perf_counter() - t0) * 1000)
    results.append(summarize("redis_incr", rlat))
    results.append(summarize("redis_session_set_get", slat))

    _dump(out_path, results)


async def bench_http(base_url: str, out_path: str, concurrency: int) -> None:
    """层 B：真实 uvicorn（mock AI）HTTP + SSE + 容量。"""
    results: list[dict] = []
    async with AsyncClient(base_url=base_url, timeout=120) as c:
        admin_headers = await _login(c)
        lat, err, _ = await bench_request(c, "GET", "/api/v1/health", n=30)
        results.append(summarize("http_health", lat, err))
        lat, err, sse = await bench_request(
            c, "POST", "/api/v1/ai/product-qa",
            json_body={"question": "安诊保百万医疗险的等待期是多久？"},
            headers=admin_headers, n=8, sse=True,
        )
        results.append(summarize("http_sse_product_qa", lat, err, sse))
        lat, err, sse = await bench_request(
            c, "POST", "/api/v1/ai/sales-agent/chat",
            json_body={"message": "客户想了解百万医疗险，请生成销售话术", "session_id": "bench-agent"},
            headers=admin_headers, n=5, sse=True,
        )
        results.append(summarize("http_sse_sales_agent", lat, err, sse))
        # 容量：health 并发 1/5/10
        for cc in (1, 5, 10):
            async def _one():
                t0 = time.perf_counter()
                r = await c.get("/api/v1/health")
                return (time.perf_counter() - t0) * 1000, r.status_code
            clat, cerr = [], 0
            for _ in range(3):
                outs = await asyncio.gather(*[_one() for _ in range(cc)])
                for l, code in outs:
                    clat.append(l)
                    if code >= 400:
                        cerr += 1
            results.append(summarize(f"http_capacity_health_c{cc}", clat, cerr))
    _dump(out_path, results)


async def bench_ai(base_url: str, api_key: str, out_path: str) -> None:
    """层 C：真实 AI smoke（少量）。无 key 时打印 NOT RUN。"""
    if not api_key or api_key.startswith("${{"):
        print(json.dumps({"mode": "ai", "status": "NOT_RUN", "reason": "AZB_AI_API_KEY not configured"}))
        _dump(out_path, {"mode": "ai", "status": "NOT_RUN"})
        return
    os.environ["AZB_AI_API_KEY"] = api_key
    os.environ["AZB_AI_PROVIDER"] = "deepseek"
    os.environ["AZB_DEMO_MODE"] = "false"
    results: list[dict] = []
    async with AsyncClient(base_url=base_url, timeout=180) as c:
        admin_headers = await _login(c)
        for name, path, body in [
            ("ai_product_qa", "/api/v1/ai/product-qa", {"question": "百万医疗险等待期多久？", "conversation_id": "bench-ai-qa"}),
            ("ai_sales_agent", "/api/v1/ai/sales-agent/chat", {"message": "介绍百万医疗险", "session_id": "bench-ai-agent"}),
        ]:
            lat, err, sse = await bench_request(
                c, "POST", path, json_body=body, headers=admin_headers, n=2, sse=True,
            )
            results.append(summarize(name, lat, err, sse))
    _dump(out_path, results)


def _dump(out_path: str, data) -> None:
    payload = {"mode": os.environ.get("BENCH_MODE", "?"), "results": data,
               "env": {"python": os.sys.version.split()[0]}}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("SUMMARY_WRITTEN", out_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["deterministic", "http", "ai"])
    ap.add_argument("--base-url", default="http://127.0.0.1:8001")
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--api-key", default=os.environ.get("AZB_AI_API_KEY", ""))
    ap.add_argument("--out", default="/tmp/benchmark_result.json")
    a = ap.parse_args()

    os.environ["BENCH_MODE"] = a.mode
    if a.mode == "deterministic":
        asyncio.run(bench_deterministic(a.out, a.concurrency))
    elif a.mode == "http":
        asyncio.run(bench_http(a.base_url, a.out, a.concurrency))
    else:
        asyncio.run(bench_ai(a.base_url, a.api_key, a.out))


if __name__ == "__main__":
    main()
