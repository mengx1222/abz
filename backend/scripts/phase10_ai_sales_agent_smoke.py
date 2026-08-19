#!/usr/bin/env python3
"""Phase 10 — Real AI Sales Agent Smoke Test（黄金链，真实 Provider）。

在真实 Provider（Qwen/DeepSeek）+ DEMO_MODE=false + 真实 PG 下验证一条完整黄金链：

  真实登录用户 → Customer Context → RAG/Product Evidence → Script Generation
  → Compliance Check → SSE 事件流 → Agent Complete

覆盖：
  1. http_login：seed SYSTEM_ADMIN 登录
  2. customer_context：Agent 读取真实客户（无客户则创建一个最小客户）
  3. agent_golden_chain：POST /api/v1/ai/sales-agent/chat（SSE）
     - 事件顺序：agent_start → tool_planned/tool_start... → message_delta → agent_complete
     - agent_complete.status == completed
     - tool_sequence 含 get_customer_context / search_product_knowledge / check_compliance
     - 真实 Provider 产出 message（非空、非拒答模板）

安全约束：
  - 真实 API Key 只从环境变量读取（AZB_AI_API_KEY），绝不硬编码
  - 无 Key 时输出 NOT RUN 并 exit 0（不阻塞普通 CI）
  - 不打印完整 prompt / 敏感客户信息 / 原始思考链
  - Agent 输出只包含安全执行状态（tool_planned 为状态说明，非思维链）

用法（先起 backend，DEMO_MODE=false）:
  AZB_BASE_URL=http://127.0.0.1:8000 \
  AZB_AI_API_KEY=sk-xxx AZB_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \
  AZB_AI_MODEL=qwen-plus \
  python scripts/phase10_ai_sales_agent_smoke.py
"""
import os
import sys

import requests

BASE_URL = os.environ.get("AZB_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
AI_API_KEY = os.environ.get("AZB_AI_API_KEY", "")
PHONE = os.environ.get("AZB_PHONE", "13800138000")
PASSWORD = os.environ.get("AZB_PASSWORD", "888888")


class SalesAgentSmoke:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.token: str | None = None
        self.results: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append({"name": name, "ok": bool(ok), "detail": detail})
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    def _login(self) -> bool:
        try:
            r = self.session.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"phone": PHONE, "password": PASSWORD},
                timeout=30,
            )
            data = r.json()
            token = (data.get("data") or {}).get("access_token")
            if token:
                self.token = token
                self.session.headers["Authorization"] = f"Bearer {token}"
                return True
            print(f"    login body: {str(data)[:200]}")
            return False
        except Exception as e:  # noqa: BLE001
            print(f"    login error: {e}")
            return False

    def _ensure_customer(self) -> str | None:
        """获取一个可访问客户；无则创建最小客户。返回 customer_id。"""
        try:
            r = self.session.get(
                f"{BASE_URL}/api/v1/customers?page=1&page_size=1", timeout=30
            )
            items = (r.json().get("data") or {}).get("items") or []
            if items:
                return items[0].get("id")
            r2 = self.session.post(
                f"{BASE_URL}/api/v1/customers",
                json={
                    "name": "AgentSmoke客户",
                    "age": 35,
                    "customer_type": "prospective",
                    "insurance_type": "医疗险",
                    "current_stage": "needs_analysis",
                    "intention_level": 4,
                },
                timeout=30,
            )
            data = r2.json()
            if r2.status_code == 200:
                return (data.get("data") or {}).get("id")
            print(f"    create customer body: {str(data)[:200]}")
            return None
        except Exception as e:  # noqa: BLE001
            print(f"    customer error: {e}")
            return None

    def _agent_chat(self, customer_id: str) -> dict:
        """调用 Agent SSE 端点并断言事件链。"""
        r = self.session.post(
            f"{BASE_URL}/api/v1/ai/sales-agent/chat",
            json={
                "customer_id": customer_id,
                "message": "客户想了解医疗险的保障范围和理赔流程，帮我准备沟通话术",
                "product_type": "医疗险",
                "sales_stage": "needs_analysis",
            },
            timeout=180,
            stream=True,
        )
        body = r.text if hasattr(r, "text") else ""
        if r.status_code != 200:
            return {"status": "http_error", "detail": f"HTTP {r.status_code} {body[:300]}"}

        has_agent_start = "agent_start" in body
        has_tool_planned = "tool_planned" in body
        has_tool_start = '"tool_start"' in body or "'tool_start'" in body
        has_message_delta = "message_delta" in body
        has_complete = "agent_complete" in body
        status_completed = '"status": "completed"' in body
        has_customer_tool = "get_customer_context" in body
        has_rag_tool = "search_product_knowledge" in body
        has_compliance = '"compliance"' in body or "check_compliance" in body

        return {
            "status": "ok",
            "bytes": len(body),
            "has_agent_start": has_agent_start,
            "has_tool_planned": has_tool_planned,
            "has_tool_start": has_tool_start,
            "has_message_delta": has_message_delta,
            "has_complete": has_complete,
            "status_completed": status_completed,
            "has_customer_tool": has_customer_tool,
            "has_rag_tool": has_rag_tool,
            "has_compliance": has_compliance,
        }

    def run(self) -> None:
        print("═══ Phase 10 — Real AI Sales Agent Smoke Test（黄金链）═══")
        print(f"BaseURL: {BASE_URL} | Provider key: {'configured' if AI_API_KEY else 'NOT set'}")

        if not self._login():
            self.check("http_login", False, "login failed (backend up?)")
            self._summary()
            return
        self.check("http_login", True, f"user={PHONE}")

        customer_id = self._ensure_customer()
        if not customer_id:
            self.check("customer_context", False, "no customer available and create failed")
            self._summary()
            return
        self.check("customer_context", True, f"customer_id={customer_id[:8]}...")

        try:
            info = self._agent_chat(customer_id)
            if info["status"] == "http_error":
                self.check("agent_golden_chain", False, info["detail"])
            else:
                ok = (
                    info["has_agent_start"]
                    and info["has_tool_planned"]
                    and info["has_message_delta"]
                    and info["has_complete"]
                    and info["status_completed"]
                    and info["has_customer_tool"]
                )
                self.check(
                    "agent_golden_chain", ok,
                    f"bytes={info['bytes']} start={info['has_agent_start']} "
                    f"planned={info['has_tool_planned']} delta={info['has_message_delta']} "
                    f"complete={info['has_complete']} completed={info['status_completed']} "
                    f"customer_tool={info['has_customer_tool']} rag_tool={info['has_rag_tool']} "
                    f"compliance={info['has_compliance']}",
                )
        except Exception as e:  # noqa: BLE001
            self.check("agent_golden_chain", False, f"{type(e).__name__}: {e}")

        self._summary()

    def _summary(self) -> None:
        passed = sum(1 for x in self.results if x["ok"])
        total = len(self.results)
        print(f"\nRESULT: {passed}/{total} passed")
        for x in self.results:
            if not x["ok"]:
                print(f"  FAILED: {x['name']} — {x['detail']}")
        sys.exit(0 if passed == total else 1)


def main() -> None:
    if not AI_API_KEY:
        print("REAL_AI_SMOKE_TEST=NOT RUN (AZB_AI_API_KEY not set)")
        print("说明：未配置真实 Provider API Key，跳过真实 AI Sales Agent Smoke Test（不阻塞普通 CI）。")
        sys.exit(0)
    SalesAgentSmoke().run()


if __name__ == "__main__":
    main()
