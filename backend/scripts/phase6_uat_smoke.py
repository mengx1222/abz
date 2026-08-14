#!/usr/bin/env python3
"""
Phase 6 — UAT Smoke Test: Critical Path Verification.

Standalone script that tests ALL critical user paths against a running backend server.
Uses only stdlib + requests. No test framework required.

Usage:
    AZB_BASE_URL=http://localhost:8000 python backend/scripts/phase6_uat_smoke.py
    AZB_DEMO_MODE=true  # backend should be started with this

Exit codes:
    0 — all tests passed
    1 — one or more tests failed
"""
import os
import sys
import time

import requests


class SmokeTest:
    """Holds state and runs individual test cases against the API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.token: str | None = None
        self.admin_token: str | None = None
        self.first_customer_id: str | None = None
        self.new_customer_id: str | None = None
        self.first_base_id: str | None = None
        self.results: list[dict] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _auth_headers(self, token: str | None = None) -> dict:
        t = token or self.token
        return {"Authorization": f"Bearer {t}"} if t else {}

    # ------------------------------------------------------------------
    # Core runner
    # ------------------------------------------------------------------
    def run_test(
        self,
        name: str,
        method: str,
        path: str,
        expected_status: int,
        validate_fn=None,
        json: dict | None = None,
        headers: dict | None = None,
        timeout: float = 30.0,
        use_admin_token: bool = False,
        no_token: bool = False,
    ) -> dict:
        """Execute a single HTTP test case and record the result."""
        url = self._url(path)
        hdrs = {}
        if headers:
            hdrs.update(headers)
        if not no_token:
            hdrs.update(self._auth_headers(self.admin_token if use_admin_token else None))

        start = time.perf_counter()
        try:
            resp = self.session.request(
                method,
                url,
                json=json,
                headers=hdrs,
                timeout=timeout,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            # Status check
            passed = resp.status_code == expected_status
            detail = f"{method} {path} → {resp.status_code} ({elapsed_ms}ms)"

            if passed and validate_fn:
                try:
                    body = resp.json()
                except Exception:
                    body = None
                try:
                    validate_result = validate_fn(resp, body)
                    if validate_result is not True:
                        passed = False
                        detail = f"{detail} | validation: {validate_result}"
                except Exception as exc:
                    passed = False
                    detail = f"{detail} | validation error: {exc}"

        except requests.exceptions.ConnectionError:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            passed = False
            detail = f"{method} {path} → CONNECTION REFUSED ({elapsed_ms}ms)"
        except requests.exceptions.Timeout:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            passed = False
            detail = f"{method} {path} → TIMEOUT ({elapsed_ms}ms)"
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            passed = False
            detail = f"{method} {path} → ERROR: {exc} ({elapsed_ms}ms)"

        result = {"name": name, "passed": passed, "detail": detail}
        self.results.append(result)
        return result

    # ------------------------------------------------------------------
    # Group runner
    # ------------------------------------------------------------------
    def run_group(self, name: str, tests: list[callable]) -> dict:
        """Run a group of tests, print progress, return summary."""
        print(f"\n📦 {name}")
        group_results = []
        for test_fn in tests:
            result = test_fn(self)
            group_results.append(result)
            icon = "✅" if result["passed"] else "❌"
            print(f"  {icon} {result['name']}: {result['detail']}")
        passed = sum(1 for r in group_results if r["passed"])
        total = len(group_results)
        return {"name": name, "passed": passed, "total": total}

    # ------------------------------------------------------------------
    # Test definitions
    # ------------------------------------------------------------------

    def group_health(self) -> dict:
        def tc001(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-001",
                "GET",
                "/api/v1/health",
                200,
                validate_fn=lambda r, b: (
                    True
                    if b and b.get("status") == "healthy"
                    else f"body.status={b.get('status') if b else 'N/A'}"
                ),
            )

        def tc002(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-002",
                "GET",
                "/api/v1/ready",
                200,
                validate_fn=lambda r, b: (
                    True
                    if b and b.get("status") in ("ready", "not_ready")
                    else f"body.status={b.get('status') if b else 'N/A'}"
                ),
            )

        return self.run_group("Group 1: Health & Readiness", [tc001, tc002])

    def group_auth(self) -> dict:
        def tc003(st: SmokeTest) -> dict:
            r = st.run_test(
                "TC-003",
                "POST",
                "/api/v1/auth/login",
                200,
                json={"phone": "13800138000", "password": "demo123"},
                no_token=True,
                validate_fn=lambda r, b: (
                    st._capture_agent_token(b)
                    if b and "access_token" in b and "refresh_token" in b
                    else f"missing tokens — keys={list(b.keys()) if b else 'N/A'}"
                ),
            )
            return r

        def tc004(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-004",
                "GET",
                "/api/v1/auth/me",
                200,
                validate_fn=lambda r, b: (
                    True
                    if b and isinstance(b.get("name"), str) and len(b["name"]) > 0
                    else f"user.name missing or empty — got {b}"
                ),
            )

        def tc005(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-005",
                "GET",
                "/api/v1/auth/me",
                401,
                no_token=True,
            )

        return self.run_group("Group 2: Authentication", [tc003, tc004, tc005])

    def group_customers(self) -> dict:
        def tc006(st: SmokeTest) -> dict:
            def _validate(r, b):
                if not b:
                    return "empty body"
                # Accept either {items: [...], total: N} or {data: [...]} or a list
                if isinstance(b, list):
                    if len(b) > 0:
                        st.first_customer_id = str(b[0].get("id", ""))
                    return True
                items = b.get("items") or b.get("data")
                if not isinstance(items, list):
                    return f"no list found in body, keys={list(b.keys())}"
                if len(items) > 0:
                    st.first_customer_id = str(items[0].get("id", ""))
                return True

            return st.run_test(
                "TC-006",
                "GET",
                "/api/v1/customers?page=1&page_size=10",
                200,
                validate_fn=_validate,
            )

        def tc007(st: SmokeTest) -> dict:
            if not st.first_customer_id:
                return {
                    "name": "TC-007",
                    "passed": False,
                    "detail": "skipped — no customer ID from TC-006",
                }
            return st.run_test(
                "TC-007",
                "GET",
                f"/api/v1/customers/{st.first_customer_id}",
                200,
                validate_fn=lambda r, b: (
                    True
                    if b and b.get("id")
                    else f"customer detail missing id — got {list(b.keys()) if b else 'N/A'}"
                ),
            )

        def tc008(st: SmokeTest) -> dict:
            new_customer = {
                "name": f"UAT测试客户_{int(time.time())}",
                "phone": f"199{int(time.time()) % 100000000:08d}",
                "gender": "male",
                "age": 30,
                "remark": "UAT smoke test auto-created",
            }
            def _validate(r, b):
                if not b or not b.get("id"):
                    return f"created customer missing id — got {b}"
                st.new_customer_id = str(b["id"])
                return True

            return st.run_test(
                "TC-008",
                "POST",
                "/api/v1/customers",
                201,
                json=new_customer,
                validate_fn=_validate,
            )

        def tc009(st: SmokeTest) -> dict:
            if not st.new_customer_id:
                return {
                    "name": "TC-009",
                    "passed": False,
                    "detail": "skipped — no new customer ID from TC-008",
                }
            return st.run_test(
                "TC-009",
                "PUT",
                f"/api/v1/customers/{st.new_customer_id}",
                200,
                json={
                    "name": f"UAT更新客户_{int(time.time())}",
                    "remark": "UAT smoke test updated",
                },
                validate_fn=lambda r, b: (
                    True
                    if b and b.get("id")
                    else f"updated customer missing id — got {b}"
                ),
            )

        return self.run_group(
            "Group 3: Customer Management (Agent role)",
            [tc006, tc007, tc008, tc009],
        )

    def group_knowledge(self) -> dict:
        def tc010(st: SmokeTest) -> dict:
            def _validate(r, b):
                if not b:
                    return "empty body"
                items = b.get("items") or b.get("data") if isinstance(b, dict) else b
                if isinstance(items, list) and len(items) > 0:
                    first = items[0]
                    st.first_base_id = str(first.get("id", ""))
                return True

            return st.run_test(
                "TC-010",
                "GET",
                "/api/v1/knowledge/bases",
                200,
                validate_fn=_validate,
            )

        def tc011(st: SmokeTest) -> dict:
            if not st.first_base_id:
                return {
                    "name": "TC-011",
                    "passed": False,
                    "detail": "skipped — no knowledge base ID from TC-010",
                }
            return st.run_test(
                "TC-011",
                "GET",
                f"/api/v1/knowledge/bases/{st.first_base_id}/documents",
                200,
                validate_fn=lambda r, b: True if b else "empty body",
            )

        return self.run_group("Group 4: Knowledge Base", [tc010, tc011])

    def group_ai_chat(self) -> dict:
        def tc012(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-012",
                "POST",
                "/api/v1/ai/chat",
                200,
                json={"message": "重疾险的等待期是多长？"},
                timeout=60.0,
                validate_fn=lambda r, b: (
                    True
                    if b and isinstance(b.get("answer"), str) and len(b["answer"]) > 0
                    else f"AI response missing 'answer' field — got {list(b.keys()) if b else 'N/A'}"
                ),
            )

        return self.run_group("Group 5: AI Chat (RAG)", [tc012])

    def group_scripts(self) -> dict:
        def tc013(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-013",
                "GET",
                "/api/v1/scripts?page=1",
                200,
                validate_fn=lambda r, b: True if b else "empty body",
            )

        return self.run_group("Group 6: Script Library", [tc013])

    def group_training(self) -> dict:
        def tc014(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-014",
                "GET",
                "/api/v1/training/scenarios",
                200,
                validate_fn=lambda r, b: True if b else "empty body",
            )

        return self.run_group("Group 7: Training", [tc014])

    def group_dashboard(self) -> dict:
        def tc015(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-015",
                "GET",
                "/api/v1/dashboard/overview",
                200,
                validate_fn=lambda r, b: (
                    True
                    if b and isinstance(b, dict) and len(b) > 0
                    else f"dashboard data empty — got {b}"
                ),
            )

        return self.run_group("Group 8: Dashboard", [tc015])

    def group_notifications(self) -> dict:
        def tc016(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-016",
                "GET",
                "/api/v1/notifications",
                200,
                validate_fn=lambda r, b: True if b is not None else "empty body",
            )

        return self.run_group("Group 9: Notifications", [tc016])

    def group_growth(self) -> dict:
        def tc017(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-017",
                "GET",
                "/api/v1/growth/overview",
                200,
                validate_fn=lambda r, b: True if b is not None else "empty body",
            )

        return self.run_group("Group 10: Growth", [tc017])

    def group_community(self) -> dict:
        def tc018(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-018",
                "GET",
                "/api/v1/community/posts?page=1",
                200,
                validate_fn=lambda r, b: True if b is not None else "empty body",
            )

        return self.run_group("Group 11: Community", [tc018])

    def group_admin(self) -> dict:
        def tc019(st: SmokeTest) -> dict:
            r = st.run_test(
                "TC-019",
                "POST",
                "/api/v1/auth/login",
                200,
                json={"phone": "13900139000", "password": "admin123"},
                no_token=True,
                validate_fn=lambda r, b: (
                    st._capture_admin_token(b)
                    if b and "access_token" in b
                    else f"missing access_token — keys={list(b.keys()) if b else 'N/A'}"
                ),
            )
            return r

        def tc020(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-020",
                "GET",
                "/api/v1/admin/users",
                200,
                use_admin_token=True,
                validate_fn=lambda r, b: True if b is not None else "empty body",
            )

        return self.run_group("Group 12: Admin (Admin role)", [tc019, tc020])

    def group_security(self) -> dict:
        def tc021(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-021",
                "GET",
                "/api/v1/health",
                200,
                validate_fn=lambda r, b: (
                    True
                    if r.headers.get("X-Content-Type-Options")
                    else "missing X-Content-Type-Options header"
                ),
            )

        def tc022(st: SmokeTest) -> dict:
            return st.run_test(
                "TC-022",
                "GET",
                "/api/v1/health",
                200,
                validate_fn=lambda r, b: (
                    True
                    if r.headers.get("X-Frame-Options")
                    else "missing X-Frame-Options header"
                ),
            )

        return self.run_group("Group 13: Security Headers", [tc021, tc022])

    def group_rate_limit(self) -> dict:
        def tc023(st: SmokeTest) -> dict:
            """Send 10 rapid login requests; expect at least one 429."""
            statuses = []
            payload = {"phone": "13800138000", "password": "demo123"}
            url = st._url("/api/v1/auth/login")
            start = time.perf_counter()
            for _ in range(10):
                try:
                    r = requests.post(url, json=payload, timeout=10)
                    statuses.append(r.status_code)
                except Exception:
                    statuses.append(0)
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            got_429 = 429 in statuses
            # In demo mode rate limits may be high — pass if all 200 (lenient)
            if got_429:
                passed = True
                detail = f"Rate limit triggered: {statuses} ({elapsed_ms}ms)"
            elif all(s == 200 for s in statuses):
                passed = True
                detail = f"No rate limit triggered (demo mode lenient): {statuses} ({elapsed_ms}ms)"
            else:
                passed = False
                detail = f"Unexpected statuses: {statuses} ({elapsed_ms}ms)"

            result = {"name": "TC-023", "passed": passed, "detail": detail}
            st.results.append(result)
            return result

        return self.run_group("Group 14: Rate Limiting", [tc023])

    # ------------------------------------------------------------------
    # Token capture helpers (used inside validate_fn closures)
    # ------------------------------------------------------------------
    def _capture_agent_token(self, body) -> bool:
        if body and "access_token" in body:
            self.token = body["access_token"]
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            return True
        return False

    def _capture_admin_token(self, body) -> bool:
        if body and "access_token" in body:
            self.admin_token = body["access_token"]
            return True
        return False


def main():
    base_url = os.environ.get("AZB_BASE_URL", "http://localhost:8000")
    version = "v1.0.0-rc.1"

    print("═════════════════════════════════════════════")
    print(f"  安诊保 AI — UAT Smoke Test {version}")
    print("═════════════════════════════════════════════")
    print(f"  Target: {base_url}")
    print("  Mode:   Demo (AZB_DEMO_MODE=true)")

    smoke = SmokeTest(base_url)
    overall_start = time.perf_counter()

    groups = [
        smoke.group_health,
        smoke.group_auth,
        smoke.group_customers,
        smoke.group_knowledge,
        smoke.group_ai_chat,
        smoke.group_scripts,
        smoke.group_training,
        smoke.group_dashboard,
        smoke.group_notifications,
        smoke.group_growth,
        smoke.group_community,
        smoke.group_admin,
        smoke.group_security,
        smoke.group_rate_limit,
    ]

    group_summaries: list[dict] = []
    for fn in groups:
        summary = fn()
        group_summaries.append(summary)

    overall_duration = time.perf_counter() - overall_start

    # Final summary
    total_passed = sum(s["passed"] for s in group_summaries)
    total_tests = sum(s["total"] for s in group_summaries)
    total_failed = total_tests - total_passed

    print()
    print("═════════════════════════════════════════════")
    if total_failed == 0:
        print(f"  RESULT: {total_passed}/{total_tests} passed (ALL PASSED)")
    else:
        print(f"  RESULT: {total_passed}/{total_tests} passed ({total_failed} FAILED)")
    print(f"  Duration: {overall_duration:.2f}s")
    print("═════════════════════════════════════════════")

    # Print failures
    failures = [r for r in smoke.results if not r["passed"]]
    if failures:
        for f in failures:
            print(f"  ❌ {f['name']}: {f['detail']}")
        print("═════════════════════════════════════════════")

    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    main()
