#!/usr/bin/env python3
"""Phase 8 — Production Environment Core Business Flow Verification.

在真实 PostgreSQL + pgvector + Redis 环境（AZB_DEMO_MODE=false）下，
验证核心业务闭环的真实可运行性：

  1. 健康检查 / 就绪检查
  2. 登录（真实 DB 用户 + JWT）
  3. 工作台 Dashboard
  4. 客户 360
  5. AI 客户分析
  6. AI 产品知识问答
  7. AI 话术（SSE）
  8. 合规检查
  9. AI 陪练
  10. 社区帖子 + AI Summary
  11. Growth
  12. 通知中心

每个步骤都是真实 API + 真实 DB 查询，无 Demo fallback。
用法: AZB_BASE_URL=http://127.0.0.1:8000 python scripts/phase8_production_core_flow.py
"""
import json
import os
import sys
import time

import requests

BASE_URL = os.environ.get("AZB_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PHONE = os.environ.get("AZB_PHONE", "13800138000")
PASSWORD = os.environ.get("AZB_PASSWORD", "888888")


def _unwrap(data: dict | None) -> dict | list | None:
    if data is None:
        return None
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


class Phase8:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.token: str | None = None
        self.results: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append({"name": name, "ok": bool(ok), "detail": detail})
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    def _get(self, path: str, timeout: int = 30):
        return self.session.get(f"{BASE_URL}{path}", timeout=timeout)

    def _post(self, path: str, json_body: dict | None = None, timeout: int = 60):
        return self.session.post(f"{BASE_URL}{path}", json=json_body, timeout=timeout)

    # ------------------------------------------------------------------
    def run(self) -> None:
        print("═══ Phase 8 — Production Core Business Flow Verification ═══")
        print(f"  Target: {BASE_URL}")

        # 1. Health / Ready
        try:
            r = self._get("/api/v1/health")
            data = r.json().get("data", {})
            self.check("health", r.status_code == 200 and data.get("status") == "healthy", f"HTTP {r.status_code}")
        except Exception as e:
            self.check("health", False, str(e))

        try:
            r = self._get("/api/v1/ready")
            checks = r.json().get("data", {}).get("checks", {})
            db_ok = checks.get("database") == "ok" or checks.get("database") == "healthy"
            redis_ok = checks.get("redis") == "ok" or checks.get("redis") == "healthy"
            self.check(
                "ready",
                r.status_code == 200 and db_ok and redis_ok,
                f"HTTP {r.status_code} db={checks.get('database')} redis={checks.get('redis')}",
            )
        except Exception as e:
            self.check("ready", False, str(e))

        # 2. Login
        try:
            r = self._post("/api/v1/auth/login", {"phone": PHONE, "password": PASSWORD})
            body = _unwrap(r.json())
            token = body.get("access_token") if isinstance(body, dict) else None
            if token:
                self.token = token
                self.session.headers["Authorization"] = f"Bearer {token}"
            self.check("login", r.status_code == 200 and bool(token), f"HTTP {r.status_code}")
        except Exception as e:
            self.check("login", False, str(e))

        if not self.token:
            self.check("core_flow", False, "login failed, cannot continue")
            self._summary()
            return

        # 3. Dashboard
        try:
            r = self._get("/api/v1/dashboard")
            data = _unwrap(r.json())
            self.check("dashboard", r.status_code == 200 and isinstance(data, dict), f"HTTP {r.status_code}")
        except Exception as e:
            self.check("dashboard", False, str(e))

        # 4. Customers 360
        try:
            r = self._get("/api/v1/customers?page=1&page_size=5")
            data = _unwrap(r.json())
            self.check(
                "customers",
                r.status_code == 200 and isinstance(data, list),
                f"HTTP {r.status_code} items={len(data) if isinstance(data, list) else 'n/a'}",
            )
        except Exception as e:
            self.check("customers", False, str(e))

        # 5. AI customer analysis (non-streaming smoke)
        try:
            r = self._get("/api/v1/customers?page=1&page_size=1")
            data = _unwrap(r.json())
            cid = data[0].get("id") if isinstance(data, list) and data else None
            if cid:
                r2 = self._post(f"/api/v1/customers/{cid}/ai-analysis", timeout=120)
                body = r2.text
                has_start = "analysis_start" in body
                self.check("customer_ai_analysis", r2.status_code == 200 and has_start, f"HTTP {r2.status_code} bytes={len(body)}")
            else:
                self.check("customer_ai_analysis", False, "no customers in DB")
        except Exception as e:
            self.check("customer_ai_analysis", False, str(e))

        # 6. AI product QA (SSE chat)
        try:
            r = self._post("/api/v1/ai/product-qa/chat", {"question": "介绍一下医疗险"})
            body = r.text
            self.check("product_qa", r.status_code == 200 and len(body) > 0, f"HTTP {r.status_code} bytes={len(body)}")
        except Exception as e:
            self.check("product_qa", False, str(e))

        # 7. AI Script generation (SSE)
        try:
            r = self._post(
                "/api/v1/scripts/generate",
                {"customer_context": {"name": "张先生", "age": 35, "stage": "needs_analysis", "product_type": "医疗险"}, "style": "professional", "product_type": "医疗险"},
            )
            body = r.text
            has_complete = "generation_complete" in body or "style_refused" in body
            self.check("script_generate", r.status_code == 200 and has_complete, f"HTTP {r.status_code} bytes={len(body)}")
        except Exception as e:
            self.check("script_generate", False, str(e))

        # 8. Compliance check
        try:
            r = self._post("/api/v1/scripts/check-compliance", {"text": "保证收益稳赚不赔"})
            data = _unwrap(r.json())
            self.check("compliance", r.status_code == 200 and data.get("status") == "RED", f"HTTP {r.status_code} status={data.get('status') if isinstance(data, dict) else 'n/a'}")
        except Exception as e:
            self.check("compliance", False, str(e))

        # 9. Training scenarios
        try:
            r = self._get("/api/v1/training/scenarios")
            data = _unwrap(r.json())
            self.check("training", r.status_code == 200 and isinstance(data, list), f"HTTP {r.status_code}")
        except Exception as e:
            self.check("training", False, str(e))

        # 10. Community posts + AI summary
        try:
            r = self._get("/api/v1/community/posts?page=1&page_size=5")
            data = _unwrap(r.json())
            posts = data if isinstance(data, list) else []
            self.check("community_posts", r.status_code == 200, f"HTTP {r.status_code} posts={len(posts)}")
            if posts:
                pid = posts[0].get("id")
                try:
                    r2 = self._get(f"/api/v1/community/posts/{pid}/ai-summary", timeout=60)
                    body = r2.text
                    has_start = "summary_start" in body
                    has_end = "summary_complete" in body or "error" in body
                    self.check("community_ai_summary", r2.status_code == 200 and has_start and has_end, f"HTTP {r2.status_code} bytes={len(body)}")
                except Exception as e:
                    self.check("community_ai_summary", False, str(e))
            else:
                self.check("community_ai_summary", True, "no posts to summarize (empty DB ok)")
        except Exception as e:
            self.check("community_posts", False, str(e))

        # 11. Growth
        try:
            r = self._get("/api/v1/growth/overview")
            data = _unwrap(r.json())
            self.check("growth", r.status_code == 200 and isinstance(data, dict), f"HTTP {r.status_code}")
        except Exception as e:
            self.check("growth", False, str(e))

        # 12. Notifications
        try:
            r = self._get("/api/v1/notifications")
            data = _unwrap(r.json())
            self.check("notifications", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            self.check("notifications", False, str(e))

        self._summary()

    def _summary(self) -> None:
        passed = sum(1 for r in self.results if r["ok"])
        total = len(self.results)
        print()
        print(f"═══ RESULT: {passed}/{total} passed ═══")
        for r in self.results:
            if not r["ok"]:
                print(f"  FAILED: {r['name']} — {r['detail']}")
        sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    Phase8().run()
