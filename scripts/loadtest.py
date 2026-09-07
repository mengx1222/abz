#!/usr/bin/env python3
"""轻量并发压测脚本（试点前容量摸底）。

用法:
    python scripts/loadtest.py [--base http://127.0.0.1:3000] \
        [--users 30] [--duration 30] [--phone 13800138000] [--password 888888]

流程: 登录一次拿 token → 按"读为主 + 少量写"混合场景并发打点 → 输出 RPS / p50 / p95 / p99 / 错误数。
端点混合（可按需增删 ENDPOINTS）: 健康检查 / Dashboard / 客户列表 / 产品知识。
不压 AI/SSE 接口（真实计费且长连接语义不同，需单独场景化压测）。

依赖: pip install httpx （便携环境自带）
"""
import argparse
import asyncio
import json
import random
import statistics
import time

import httpx

DEFAULT_BASE = "http://127.0.0.1:3000"


def build_endpoints(base: str) -> list[tuple[str, str]]:
    """(method, path) 混合读场景；权重通过重复条目表达。"""
    return [
        ("GET", "/api/v1/ready"),
        ("GET", "/api/v1/ready"),
        ("GET", "/api/v1/dashboard"),
        ("GET", "/api/v1/dashboard"),
        ("GET", "/api/v1/customers"),
        ("GET", "/api/v1/customers"),
        ("GET", "/api/v1/notifications"),
        ("GET", "/api/v1/growth/overview"),
    ]


async def login(base: str, phone: str, password: str) -> str | None:
    """登录拿 token；演示模式用验证码字段也可（此处统一走密码）。"""
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{base}/api/v1/auth/login",
            json={"phone": phone, "password": password},
        )
        if r.status_code == 200:
            return r.json()["data"]["access_token"]
        # 演示模式可能只收验证码字段
        r2 = await c.post(
            f"{base}/api/v1/auth/login",
            json={"phone": phone, "verification_code": password},
        )
        if r2.status_code == 200:
            return r2.json()["data"]["access_token"]
    return None


async def worker(
    client: httpx.AsyncClient,
    endpoints: list[tuple[str, str]],
    token: str | None,
    deadline: float,
    latencies: list[float],
    errors: list[str],
    lock: asyncio.Lock,
) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    while time.monotonic() < deadline:
        method, path = random.choice(endpoints)
        start = time.monotonic()
        try:
            resp = await client.request(method, path, headers=headers)
            ok = resp.status_code < 400
            if not ok:
                async with lock:
                    errors.append(f"{resp.status_code} {path}")
        except Exception as e:  # noqa: BLE001
            ok = False
            async with lock:
                errors.append(f"{type(e).__name__} {path}")
        async with lock:
            latencies.append(time.monotonic() - start)
            _ = ok


def percentile(sorted_lat: list[float], p: float) -> float:
    if not sorted_lat:
        return 0.0
    idx = min(int(len(sorted_lat) * p), len(sorted_lat) - 1)
    return sorted_lat[idx]


async def main() -> None:
    parser = argparse.ArgumentParser(description="轻量并发压测")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--users", type=int, default=30)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--phone", default="13800138000")
    parser.add_argument("--password", default="888888")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    print(f"==> 登录 {base} (phone={args.phone}) ...")
    token = await login(base, args.phone, args.password)
    print(f"    token: {'OK' if token else 'FAILED(将以匿名压公开端点)'}")

    endpoints = build_endpoints(base)
    latencies: list[float] = []
    errors: list[str] = []
    lock = asyncio.Lock()

    async with httpx.AsyncClient(
        base_url=base, timeout=httpx.Timeout(30.0, connect=10.0), limits=httpx.Limits(max_connections=args.users * 2)
    ) as client:
        deadline = time.monotonic() + args.duration
        print(f"==> 压测开始: {args.users} 并发 × {args.duration}s, {len(endpoints)} 个端点混合 ...")
        start = time.monotonic()
        await asyncio.gather(
            *[worker(client, endpoints, token, deadline, latencies, errors, lock) for _ in range(args.users)]
        )
        elapsed = time.monotonic() - start

    lat_sorted = sorted(latencies)
    total = len(lat_sorted)
    err_count = len(errors)
    print("\n========== 压测结果 ==========")
    print(f"并发数          : {args.users}")
    print(f"实际时长        : {elapsed:.1f}s")
    print(f"总请求数        : {total}")
    print(f"吞吐 (RPS)      : {total / elapsed:.1f}")
    if lat_sorted:
        print(f"延迟 p50        : {percentile(lat_sorted, 0.50) * 1000:.0f} ms")
        print(f"延迟 p95        : {percentile(lat_sorted, 0.95) * 1000:.0f} ms")
        print(f"延迟 p99        : {percentile(lat_sorted, 0.99) * 1000:.0f} ms")
        print(f"延迟 max        : {lat_sorted[-1] * 1000:.0f} ms")
    print(f"错误数          : {err_count}")
    if errors:
        from collections import Counter

        for pattern, n in Counter(errors).most_common(5):
            print(f"  {n:5d} × {pattern}")
    print("==============================")
    print("判定参考: p95 < 1s 且错误率 < 0.1% → 试点容量 OK（30 并发 ≈ 30 人同时在线高峰）")


if __name__ == "__main__":
    asyncio.run(main())
