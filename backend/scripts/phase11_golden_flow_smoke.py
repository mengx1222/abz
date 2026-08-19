"""Phase 11 — Real AI Golden Business Flow Smoke Test（Task 29）

完整「销售准备黄金流程」真实 AI 验证（API 级 Smoke）：
  登录（AGENT）→ 客户（确定性：E2E-黄金链客户/医疗险）→ AI Sales Agent
  （SSE：agent_start/tool_planned/rag_context/citation/agent_complete/compliance）
  → Training（确定性场景 2 轮 SSE 陪练 + 结束评分非空）
  → Growth（overview.ability_scores 非空 = 训练评分进入成长体系；total_exp≥10）

- 环境：DEMO_MODE=false + 真实 AI Provider（DashScope/Qwen，Secrets 注入）
- 仅当 AZB_AI_API_KEY 配置时执行（opt-in，workflow_dispatch / REAL_AI_SMOKE_TEST）
- 退出码 0 = PASS；任何一步失败退出码 1
- 日志不打印 prompt/API Key/敏感客户数据
"""
from __future__ import annotations

import os
import sys

import requests

BASE_URL = os.environ.get("AZB_BASE_URL", "http://127.0.0.1:8000")
AI_API_KEY = os.environ.get("AZB_AI_API_KEY", "")

PHONE = "13800138000"  # seed 固定 AGENT
PASSWORD = "888888"

CUSTOMER_NAME = "E2E-黄金链客户"
CUSTOMER_PHONE = "13900002222"
SCENARIO_TITLE = '"太贵了" — 重疾险价格犹豫'

TRAINING_ROUNDS = [
    "您好，我了解您对保费有些顾虑，能说说主要担心什么吗？",
    "我理解您的想法，保费是长期投入，但保障是应对风险的关键，我们可以看看更合适的方案。",
]


class GoldenFlowSmoke:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.token: str | None = None
        self.results: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append({"name": name, "ok": bool(ok), "detail": detail})
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    # ---- 登录 ----
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

    # ---- 确定性客户（幂等创建/更新，insurance_type=医疗险 → RAG 命中） ----
    def _ensure_customer(self) -> str | None:
        try:
            r = self.session.get(
                f"{BASE_URL}/api/v1/customers?search={CUSTOMER_PHONE}&page=1&page_size=10",
                timeout=30,
            )
            items = (r.json().get("data") or {}).get("items") or []
            for c in items:
                if c.get("phone") == CUSTOMER_PHONE and c.get("name") == CUSTOMER_NAME:
                    cid = c["id"]
                    # 更新 insurance_type（保证 RAG 命中医疗险 KB）
                    self.session.put(
                        f"{BASE_URL}/api/v1/customers/{cid}",
                        json={"insurance_type": "医疗险"},
                        timeout=30,
                    )
                    return cid
            r2 = self.session.post(
                f"{BASE_URL}/api/v1/customers",
                json={
                    "name": CUSTOMER_NAME,
                    "phone": CUSTOMER_PHONE,
                    "age": 38,
                    "customer_type": "personal",
                    "insurance_type": "医疗险",
                    "current_stage": "needs_analysis",
                    "intention_level": 4,
                },
                timeout=30,
            )
            data = r2.json()
            if r2.status_code in (200, 201):
                return (data.get("data") or {}).get("id")
            print(f"    create customer body: {str(data)[:200]}")
            return None
        except Exception as e:  # noqa: BLE001
            print(f"    customer error: {e}")
            return None

    # ---- Agent 黄金链（真实 AI + RAG + Citation + Compliance） ----
    def _agent_chat(self, customer_id: str) -> dict:
        try:
            r = self.session.post(
                f"{BASE_URL}/api/v1/ai/sales-agent/chat",
                json={
                    "customer_id": customer_id,
                    "message": "客户想了解医疗险的保障范围和理赔流程，帮我准备沟通话术",
                    "product_type": "医疗险",
                    "sales_stage": "needs_analysis",
                },
                timeout=240,
                stream=True,
            )
            body = r.text if hasattr(r, "text") else ""
            if r.status_code != 200:
                return {"status": "http_error", "detail": f"HTTP {r.status_code} {body[:300]}"}
            return {
                "status": "ok",
                "bytes": len(body),
                "agent_start": "agent_start" in body,
                "tool_planned": "tool_planned" in body,
                "rag_context": '"rag_context"' in body,
                "citation": '"citation"' in body,
                "message_delta": "message_delta" in body,
                "agent_complete": "agent_complete" in body,
                "status_completed": '"status": "completed"' in body,
                "customer_tool": "get_customer_context" in body,
                "rag_tool": "search_product_knowledge" in body,
                "script_tool": "generate_sales_script" in body,
                "compliance": '"compliance"' in body or "check_compliance" in body,
            }
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "detail": f"{type(e).__name__}: {e}"}

    # ---- Training（确定性场景 2 轮 + 评分） ----
    def _training(self) -> dict:
        try:
            r = self.session.get(f"{BASE_URL}/api/v1/training/scenarios", timeout=30)
            scenarios = (r.json().get("data") or [])
            scenario = next((s for s in scenarios if s.get("title") == SCENARIO_TITLE), None)
            if not scenario:
                return {"status": "error", "detail": f"scenario not found: {SCENARIO_TITLE}"}

            r2 = self.session.post(
                f"{BASE_URL}/api/v1/training/sessions",
                json={"scenario_id": scenario["id"]},
                timeout=30,
            )
            session_id = (r2.json().get("data") or {}).get("id")
            if not session_id:
                return {"status": "error", "detail": f"start session: {r2.status_code} {r2.text[:200]}"}

            # 2 轮陪练（SSE 流式，每轮等 turn_complete）
            for i, msg in enumerate(TRAINING_ROUNDS, 1):
                r3 = self.session.post(
                    f"{BASE_URL}/api/v1/training/sessions/{session_id}/messages",
                    json={"content": msg},
                    timeout=120,
                    stream=True,
                )
                if r3.status_code != 200:
                    return {"status": "error", "detail": f"round {i} HTTP {r3.status_code} {r3.text[:200]}"}

            # 结束训练 → 评分 SSE
            r4 = self.session.post(
                f"{BASE_URL}/api/v1/training/sessions/{session_id}/complete",
                timeout=180,
                stream=True,
            )
            body = r4.text if hasattr(r4, "text") else ""
            if r4.status_code != 200:
                return {"status": "error", "detail": f"complete HTTP {r4.status_code} {body[:200]}"}
            has_score = '"score_data"' in body or "total_score" in body
            has_done = "scoring_complete" in body
            # 从 score_data 提取总分（真实 AI 评分，0-100）
            import re

            m = re.search(r'"total_score"\s*:\s*([0-9]+)', body)
            total_score = int(m.group(1)) if m else None
            return {
                "status": "ok",
                "session_id": session_id,
                "has_score": has_score,
                "has_done": has_done,
                "total_score": total_score,
                "rounds": len(TRAINING_ROUNDS),
            }
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "detail": f"{type(e).__name__}: {e}"}

    # ---- Growth（训练数据连续性：ability_scores 来自训练评分，total_exp = 训练次数×10） ----
    def _growth_overview(self) -> dict:
        try:
            r = self.session.get(f"{BASE_URL}/api/v1/growth/overview", timeout=30)
            if r.status_code != 200:
                return {"status": "error", "detail": f"HTTP {r.status_code} {r.text[:200]}"}
            body = r.json()
            ability = body.get("ability_scores") or []
            return {
                "status": "ok",
                "ability_labels": [a.get("label") for a in ability],
                "ability_nonempty": len(ability) > 0,
                "total_exp": body.get("total_exp", 0),
                "level": body.get("level"),
            }
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "detail": f"{type(e).__name__}: {e}"}

    def run(self) -> None:
        print("═══ Phase 11 — Real AI Golden Business Flow Smoke Test（完整黄金链）═══")
        print(f"BaseURL: {BASE_URL} | Provider key: {'configured' if AI_API_KEY else 'NOT set'}")

        if not self._login():
            self.check("login", False, "login failed (backend up?)")
            self._summary()
            return
        self.check("login", True, f"user={PHONE}")

        customer_id = self._ensure_customer()
        if not customer_id:
            self.check("customer_deterministic", False, "golden customer create/update failed")
            self._summary()
            return
        self.check("customer_deterministic", True, f"customer_id={customer_id[:8]}...")

        # 1) Agent 黄金链（真实 AI + RAG + Citation + Compliance）
        agent = self._agent_chat(customer_id)
        if agent["status"] != "ok":
            self.check("agent_golden_chain", False, agent["detail"])
        else:
            ok = (
                agent["agent_start"] and agent["tool_planned"]
                and agent["rag_context"] and agent["citation"]
                and agent["message_delta"] and agent["agent_complete"]
                and agent["status_completed"] and agent["customer_tool"]
                and agent["rag_tool"] and agent["script_tool"] and agent["compliance"]
            )
            self.check(
                "agent_golden_chain", ok,
                f"bytes={agent['bytes']} start={agent['agent_start']} "
                f"planned={agent['tool_planned']} rag_context={agent['rag_context']} "
                f"citation={agent['citation']} delta={agent['message_delta']} "
                f"complete={agent['agent_complete']} completed={agent['status_completed']} "
                f"customer={agent['customer_tool']} rag={agent['rag_tool']} "
                f"script={agent['script_tool']} compliance={agent['compliance']}",
            )

        # 2) Training（2 轮陪练 + 评分）
        train = self._training()
        if train["status"] != "ok":
            self.check("training_complete", False, train["detail"])
        else:
            ok = train["has_score"] and train["has_done"] and (train["total_score"] or 0) > 0
            self.check(
                "training_complete", ok,
                f"rounds={train['rounds']} score={train['total_score']} "
                f"score_data={train['has_score']} scoring_complete={train['has_done']}",
            )

        # 3) Growth（训练数据进入成长体系，同用户数据连续）
        growth = self._growth_overview()
        if growth["status"] != "ok":
            self.check("growth_reflects_training", False, growth["detail"])
        else:
            ok = growth["ability_nonempty"] and growth["total_exp"] >= 10
            self.check(
                "growth_reflects_training", ok,
                f"ability={growth['ability_labels']} total_exp={growth['total_exp']} "
                f"level={growth['level']}",
            )

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
        print("说明：未配置真实 Provider API Key，跳过真实 AI Golden Flow Smoke Test（不阻塞普通 CI）。")
        sys.exit(0)
    GoldenFlowSmoke().run()


if __name__ == "__main__":
    main()
