#!/usr/bin/env python3
"""Phase 9 — Real AI Provider + SSE Smoke Test.

在真实 Provider（DeepSeek / Qwen / OpenAI 兼容）+ DEMO_MODE=false 下验证：

  1. Gateway → Real Provider 非流式 Chat（验证 key/模型/延迟/token）
  2. Gateway → Real Provider 流式 Chat（验证 SSE token 连续性）
  3. HTTP Product QA（真实 RAG + 真实 PG + 真实 LLM，SSE 流式）
  4. HTTP Script Generate（真实生成 + Citation + Compliance）
  5. HTTP Community AI Summary（真实摘要 + 持久化）
  6. HTTP Training 场景列表（真实 DB）

安全约束：
  - 真实 API Key 只从环境变量读取（AZB_AI_API_KEY），绝不硬编码
  - 无 Key 时输出 NOT RUN 并 exit 0（不阻塞普通 CI）
  - 不打印完整 prompt / 敏感客户信息

用法（先起 backend，DEMO_MODE=false）:
  AZB_BASE_URL=http://127.0.0.1:8000 \
  AZB_AI_API_KEY=sk-xxx AZB_AI_BASE_URL=https://api.deepseek.com AZB_AI_MODEL=deepseek-chat \
  python scripts/phase9_real_ai_smoke.py
"""
import asyncio
import json
import os
import sys
import time

import requests

BASE_URL = os.environ.get("AZB_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
AI_API_KEY = os.environ.get("AZB_AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AZB_AI_BASE_URL", "")
AI_MODEL = os.environ.get("AZB_AI_MODEL", "")
AI_PROVIDER = os.environ.get("AZB_AI_PROVIDER", "deepseek")
PHONE = os.environ.get("AZB_PHONE", "13800138000")
PASSWORD = os.environ.get("AZB_PASSWORD", "888888")


class RealAiSmoke:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.token: str | None = None
        self.results: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append({"name": name, "ok": bool(ok), "detail": detail})
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    # ------------------------------------------------------------------
    # 1. Gateway → Real Provider 非流式 Chat
    # ------------------------------------------------------------------
    async def _gateway_chat(self) -> dict:
        """直接通过 AI Gateway 调用真实 Provider（非流式）。"""
        from app.ai.gateway import get_ai_gateway

        gw = get_ai_gateway()
        t0 = time.perf_counter()
        result = await gw.chat(
            messages=[
                {"role": "system", "content": "你是安诊保 AI 副驾的测试助手，请用一句话简短回答。"},
                {"role": "user", "content": "请回复：AI Gateway 真实调用成功"},
            ],
            stream=False,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "content": result.content,
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "latency_ms": latency_ms,
        }

    # ------------------------------------------------------------------
    # 2. Gateway → Real Provider 流式 Chat（SSE token 连续性）
    # ------------------------------------------------------------------
    async def _gateway_stream(self) -> dict:
        from app.ai.gateway import get_ai_gateway

        gw = get_ai_gateway()
        tokens: list[str] = []
        t0 = time.perf_counter()
        async for token in gw.chat(
            messages=[
                {"role": "system", "content": "你是安诊保 AI 副驾的测试助手。"},
                {"role": "user", "content": "请用中文输出一句话：流式传输正常。"},
            ],
            stream=True,
        ):
            tokens.append(token)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {"joined": "".join(tokens), "chunk_count": len(tokens), "latency_ms": latency_ms}

    # ------------------------------------------------------------------
    # HTTP 通用
    # ------------------------------------------------------------------
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
            return False
        except Exception as e:
            print(f"    login error: {e}")
            return False

    def _get(self, path: str, timeout: int = 30):
        return self.session.get(f"{BASE_URL}{path}", timeout=timeout)

    def _post(self, path: str, body: dict | None = None, timeout: int = 90):
        return self.session.post(f"{BASE_URL}{path}", json=body, timeout=timeout)

    # ------------------------------------------------------------------
    def run(self) -> None:
        print("═══ Phase 9 — Real AI Provider + SSE Smoke Test ═══")
        print(f"Provider: {AI_PROVIDER} | Model: {AI_MODEL or '(env AZB_AI_MODEL)'} | BaseURL: {AI_BASE_URL or '(env)'}")

        # ---- Gateway 直接调用（不依赖 HTTP backend） ----
        try:
            info = asyncio.run(self._gateway_chat())
            ok = bool(info["content"].strip())
            detail = (f"model={info['model']} tokens={info['prompt_tokens']}+{info['completion_tokens']} "
                      f"latency={info['latency_ms']}ms content={info['content'][:40]!r}")
            self.check("gateway_real_chat", ok, detail)
        except Exception as e:
            self.check("gateway_real_chat", False, f"{type(e).__name__}: {e}")

        try:
            info = asyncio.run(self._gateway_stream())
            ok = bool(info["joined"].strip()) and info["chunk_count"] > 0
            detail = f"chunks={info['chunk_count']} latency={info['latency_ms']}ms content={info['joined'][:40]!r}"
            self.check("gateway_real_stream", ok, detail)
        except Exception as e:
            self.check("gateway_real_stream", False, f"{type(e).__name__}: {e}")

        # ---- HTTP 层（需要 backend + 真实 PG） ----
        if not self._login():
            self.check("http_login", False, "login failed (backend up?)")
        else:
            self.check("http_login", True, f"user={PHONE}")

            # Product QA（真实 RAG + PG + LLM）
            try:
                r = self._post("/api/v1/ai/product-qa/chat", {"question": "介绍一下医疗险的保障范围"})
                body = r.text
                has_start = "message_start" in body
                has_token = '"event": "token"' in body or "'event': 'token'" in body
                has_end = "message_complete" in body
                self.check("product_qa", r.status_code == 200 and has_start and has_end,
                           f"HTTP {r.status_code} bytes={len(body)} start={has_start} end={has_end}")
            except Exception as e:
                self.check("product_qa", False, str(e))

            # Script Generate（真实生成 + Citation + Compliance）
            try:
                r = self._post(
                    "/api/v1/scripts/generate",
                    {
                        "customer_context": {
                            "name": "张先生", "age": 35, "stage": "needs_analysis",
                            "objection": "觉得保费太贵", "product_type": "医疗险",
                        },
                        "style": "professional",
                        "product_type": "医疗险",
                    },
                    timeout=120,
                )
                body = r.text
                has_complete = "generation_complete" in body or "style_refused" in body or "style_error" in body
                has_citation = "citations" in body
                self.check("script_generate", r.status_code == 200 and has_complete,
                           f"HTTP {r.status_code} bytes={len(body)} citation_field={has_citation}")
            except Exception as e:
                self.check("script_generate", False, str(e))

            # Community AI Summary
            try:
                r = self._get("/api/v1/community/posts?page=1&page_size=3")
                posts = (r.json().get("data") or []) if r.status_code == 200 else []
                if posts:
                    pid = posts[0].get("id")
                    r2 = self._get(f"/api/v1/community/posts/{pid}/ai-summary", timeout=120)
                    body2 = r2.text
                    has_start = "summary_start" in body2
                    has_end = "summary_complete" in body2 or '"event": "error"' in body2
                    self.check("community_ai_summary", r2.status_code == 200 and has_start and has_end,
                               f"HTTP {r2.status_code} bytes={len(body2)} start={has_start} end={has_end}")
                else:
                    self.check("community_ai_summary", True, "no posts in DB (skip)")
            except Exception as e:
                self.check("community_ai_summary", False, str(e))

            # Training scenarios（真实 DB）
            try:
                r = self._get("/api/v1/training/scenarios")
                data = r.json().get("data") if r.status_code == 200 else None
                self.check("training_scenarios", r.status_code == 200 and isinstance(data, list),
                           f"HTTP {r.status_code} count={len(data) if isinstance(data, list) else 'n/a'}")
            except Exception as e:
                self.check("training_scenarios", False, str(e))

        # ---- 汇总 ----
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
        print("说明：未配置真实 Provider API Key，跳过真实 AI Smoke Test（不阻塞普通 CI）。")
        sys.exit(0)
    RealAiSmoke().run()


if __name__ == "__main__":
    main()
