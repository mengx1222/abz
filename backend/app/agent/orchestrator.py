"""AI Sales Agent —— Orchestrator（确定性黄金链编排 + SSE 事件流）。

编排流程（安全顺序，Step 9）：
    sanitize → get_customer_context → get_customer_activity
    → search_product_knowledge（RAG + Citation；REFUSE 则跳过话术生成）
    → generate_sales_script（复用 ScriptService 内部 RAG+Confidence+Compliance+持久化）
    → check_compliance（最终校验，RED 阻止标记可用）
    → LLM 汇总（仅工具结果摘要，不泄露 CoT/内部 prompt）→ agent_complete

安全边界：
- 工具只能来自白名单 ToolRegistry；Agent 不直接访问 ORM / Provider SDK
- 所有工具携带当前 User，底层 Service 再次执行 RBAC/组织范围检查
- RAG REFUSE 后禁止模型编造产品事实；Provider 失败禁止 fallback Mock
- 最大工具调用数 / 循环检测 / 超时；session 为进程内内存（显式限制，写入 release-readiness）
"""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from structlog import get_logger

from app.agent.registry import ERROR_TOOL_TIMEOUT, ToolRegistry
from app.agent.tools import build_default_registry
from app.core.config import settings
from app.rag.safety import SeverityLevel, sanitize_user_input

logger = get_logger()

# ---- 成本/安全边界（保守值，基于当前 Provider/系统限制）----
MAX_TOOL_CALLS = 8          # 单次 Agent 请求最大工具调用数（黄金链固定 4-5，余量防循环）
MAX_TOOL_LOOP = 3           # 连续相同工具调用上限（循环检测）
AGENT_REQUEST_TIMEOUT = 90  # 单次 Agent 请求整体超时（秒）
MAX_SESSION_HISTORY = 8     # 内存 session 保留最近消息条数
MAX_SUMMARY_CHARS = 6000    # 发送给模型的工具结果摘要上限

_REFUSE_INJECTION_TEXT = "抱歉，我无法处理这个请求。请描述您的真实客户沟通需求。"
_REFUSE_RAG_TEXT = "当前知识库未找到该产品的充分产品依据。为避免编造产品条款（承保/理赔/责任等），本次未生成具体产品话术。建议补充产品知识文档后重试，或咨询华安保险产品部门。"


def _event(event_type: str, data: dict) -> str:
    """构造 SSE 事件 JSON（与 ai.py / script_service 同格式）。"""
    return json.dumps({"event": event_type, "data": data}, ensure_ascii=False)


@dataclass
class AgentSession:
    """最小可用会话上下文（进程内内存，显式限制见 release-readiness）。

    不做复杂长期记忆；仅保留最近 N 条消息 + 当前客户/产品/阶段。
    """
    session_id: str
    customer_id: str | None = None
    product_type: str | None = None
    sales_stage: str | None = None
    history: list[dict] = field(default_factory=list)  # {"role": ..., "summary": ...}
    tool_sequence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class SalesAgentService:
    """AI Sales Agent Orchestrator。"""

    def __init__(self, db: Any, registry: ToolRegistry | None = None) -> None:
        self.db = db
        self.registry = registry or build_default_registry()
        self._sessions: dict[str, AgentSession] = {}

    # ------------------------------------------------------------------
    # Session（最小上下文）
    # ------------------------------------------------------------------

    def _get_or_create_session(
        self, session_id: str | None, customer_id: str | None,
        product_type: str | None, sales_stage: str | None,
    ) -> AgentSession:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.customer_id = customer_id or session.customer_id
            session.product_type = product_type or session.product_type
            session.sales_stage = sales_stage or session.sales_stage
        else:
            session = AgentSession(
                session_id=session_id or str(uuid.uuid4()),
                customer_id=customer_id,
                product_type=product_type,
                sales_stage=sales_stage,
            )
        session.updated_at = time.time()
        if session.session_id not in self._sessions:
            self._sessions[session.session_id] = session
        return session

    def _remember(self, session: AgentSession, role: str, summary: str) -> None:
        session.history.append({"role": role, "summary": summary[:300]})
        if len(session.history) > MAX_SESSION_HISTORY:
            session.history = session.history[-MAX_SESSION_HISTORY:]

    # ------------------------------------------------------------------
    # 预算/循环防护（Step 12）
    # ------------------------------------------------------------------

    def _check_budget(self, tool_sequence: list[str], name: str) -> None:
        """每次工具调用前的成本/循环防护。"""
        if len(tool_sequence) >= MAX_TOOL_LOOP and tool_sequence[-MAX_TOOL_LOOP:] == [name] * MAX_TOOL_LOOP:
            raise AgentLoopError(f"工具 {name} 连续调用超过 {MAX_TOOL_LOOP} 次，已安全终止")
        if len(tool_sequence) >= MAX_TOOL_CALLS:
            raise AgentBudgetError(f"工具调用超过上限 {MAX_TOOL_CALLS} 次，已安全终止")

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def chat(
        self,
        user: Any,
        customer_id: str,
        message: str,
        product_type: str | None = None,
        sales_stage: str | None = None,
        session_id: str | None = None,
        request_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """AI Sales Agent 主入口（SSE 事件流）。

        Args:
            user: 当前登录用户（已通过 get_current_user，含 RBAC/组织范围）
            customer_id: 目标客户 ID
            message: 用户意图/消息
            product_type: 可选产品类型（如"医疗险"）
            sales_stage: 可选销售阶段
            session_id: 会话 ID（为空则创建新会话）
            request_id: 请求 ID（日志追踪）
        """
        request_id = request_id or str(uuid.uuid4())
        t0 = time.perf_counter()
        session = self._get_or_create_session(session_id, customer_id, product_type, sales_stage)
        tool_sequence: list[str] = []
        tool_results: dict[str, Any] = {}
        status = "completed"
        rag_status = "UNKNOWN"
        citations: list[dict] = []
        compliance_result: dict | None = None
        final_message = ""

        try:
            # ---- Step 0: 输入消毒 + Prompt Injection 检测 ----
            sanitized, safety_check = sanitize_user_input(message)
            if safety_check.is_malicious and safety_check.severity == SeverityLevel.HIGH:
                status = "refused"
                final_message = _REFUSE_INJECTION_TEXT
                yield _event("agent_start", {
                    "request_id": request_id, "session_id": session.session_id,
                    "customer_id": customer_id, "product_type": product_type,
                })
                yield _event("agent_complete", {
                    "request_id": request_id, "session_id": session.session_id,
                    "status": "refused", "message": final_message,
                    "tool_sequence": tool_sequence,
                    "reason": "prompt_injection_high",
                })
                self._remember(session, "user", message)
                self._remember(session, "assistant", final_message)
                return

            yield _event("agent_start", {
                "request_id": request_id, "session_id": session.session_id,
                "customer_id": customer_id, "product_type": product_type,
                "sales_stage": sales_stage,
            })

            customer_ctx: dict = {}

            # ---- Step 1: Customer Context ----
            yield _event("tool_planned", {"tool": "get_customer_context", "action": "正在查询客户信息"})
            yield _event("tool_start", {"tool": "get_customer_context"})
            res = await self.registry.execute(
                "get_customer_context", user=user, db=self.db,
                args={"customer_id": customer_id}, context={},
            )
            self._check_budget(tool_sequence, "get_customer_context")
            tool_sequence.append("get_customer_context")
            if not res.ok:
                # 客户不存在 / 越权 → 明确终止（错误语义），不继续生成
                status = "error"
                final_message = res.message
                yield _event("tool_result", {
                    "tool": "get_customer_context", "ok": False,
                    "error_type": res.error_type, "message": res.message,
                })
                yield _event("agent_complete", {
                    "request_id": request_id, "session_id": session.session_id,
                    "status": "error", "message": final_message,
                    "tool_sequence": tool_sequence, "reason": res.error_type,
                })
                self._remember(session, "user", message)
                self._remember(session, "assistant", final_message)
                return
            customer_ctx = res.data.get("customer") or {}
            tool_results["get_customer_context"] = res.data
            yield _event("tool_result", {
                "tool": "get_customer_context", "ok": True,
                "message": res.message, "summary": f"客户：{customer_ctx.get('name', '')} 类型：{customer_ctx.get('customer_type', '未知')}",
            })

            # ---- Step 2: Customer Activity ----
            yield _event("tool_planned", {"tool": "get_customer_activity", "action": "正在查询客户沟通历史"})
            yield _event("tool_start", {"tool": "get_customer_activity"})
            res = await self.registry.execute(
                "get_customer_activity", user=user, db=self.db,
                args={"customer_id": customer_id}, context={},
            )
            self._check_budget(tool_sequence, "get_customer_activity")
            tool_sequence.append("get_customer_activity")
            activity_summary = ""
            if res.ok:
                tool_results["get_customer_activity"] = res.data
                activity_summary = (
                    f"互动 {res.data.get('interactions_count', 0)} 条，"
                    f"待办跟进 {len(res.data.get('pending_followups') or [])} 条"
                )
                yield _event("tool_result", {
                    "tool": "get_customer_activity", "ok": True,
                    "message": res.message, "summary": activity_summary,
                })
            else:
                # activity 失败不阻断（历史缺失不影响主流程），但透传错误语义
                yield _event("tool_result", {
                    "tool": "get_customer_activity", "ok": False,
                    "error_type": res.error_type, "message": res.message,
                })

            # ---- Step 3: RAG / Product Evidence ----
            effective_product_type = product_type or customer_ctx.get("product_type")
            context: dict[str, Any] = {"customer": customer_ctx, "activity": activity_summary}
            if effective_product_type:
                yield _event("tool_planned", {"tool": "search_product_knowledge", "action": "正在检索产品依据"})
                yield _event("tool_start", {"tool": "search_product_knowledge"})
                rag_res = await self.registry.execute(
                    "search_product_knowledge", user=user, db=self.db,
                    args={
                        "question": f"{effective_product_type} 产品特点 保障范围 保费 理赔",
                        "product_type": effective_product_type,
                    },
                    context=context,
                )
                self._check_budget(tool_sequence, "search_product_knowledge")
                tool_sequence.append("search_product_knowledge")
                if rag_res.ok:
                    rag_status = rag_res.data.get("rag_status", "UNKNOWN")
                    citations = rag_res.data.get("citations") or []
                    tool_results["search_product_knowledge"] = rag_res.data
                    yield _event("rag_context", {
                        "product_type": effective_product_type,
                        "status": rag_status,
                        "confidence": rag_res.data.get("confidence"),
                        "top_score": rag_res.data.get("top_score"),
                        "sources_count": rag_res.data.get("sources_count"),
                        "citations": citations,
                    })
                    yield _event("tool_result", {
                        "tool": "search_product_knowledge", "ok": True,
                        "message": rag_res.message, "summary": f"RAG 状态：{rag_status}（来源 {rag_res.data.get('sources_count', 0)} 条）",
                    })
                else:
                    rag_status = rag_res.data.get("rag_status", "ERROR") if rag_res.data else "ERROR"
                    yield _event("rag_context", {
                        "product_type": effective_product_type, "status": rag_status,
                        "citations": [], "message": rag_res.message,
                    })
                    yield _event("tool_result", {
                        "tool": "search_product_knowledge", "ok": False,
                        "error_type": rag_res.error_type, "message": rag_res.message,
                    })
            else:
                yield _event("tool_planned", {"tool": "search_product_knowledge", "action": "未提供产品类型，跳过产品依据检索"})

            # ---- Step 4: Script Generation（RAG REFUSE 时跳过，避免编造/成本）----
            if effective_product_type and rag_status == "REFUSE":
                yield _event("tool_planned", {"tool": "generate_sales_script", "action": "RAG 无充分依据，跳过话术生成（不编造产品事实）"})
            else:
                yield _event("tool_planned", {"tool": "generate_sales_script", "action": "正在生成销售话术"})
                yield _event("tool_start", {"tool": "generate_sales_script"})
                script_res = await self.registry.execute(
                    "generate_sales_script", user=user, db=self.db,
                    args={
                        "customer_context": customer_ctx,
                        "product_type": effective_product_type,
                        "style": _default_style(sales_stage),
                    },
                    context=context,
                )
                self._check_budget(tool_sequence, "generate_sales_script")
                tool_sequence.append("generate_sales_script")
                if script_res.ok:
                    tool_results["generate_sales_script"] = script_res.data
                    scripts = script_res.data.get("scripts") or []
                    if scripts:
                        yield _event("tool_result", {
                            "tool": "generate_sales_script", "ok": True,
                            "message": script_res.message,
                            "summary": f"已生成 {len(scripts)} 条话术（合规 {script_res.data.get('compliance_status')}）",
                        })
                    else:
                        # 全部拒答（REFUSE 透传）
                        rag_status = script_res.data.get("rag_status") or rag_status
                        yield _event("tool_result", {
                            "tool": "generate_sales_script", "ok": True,
                            "message": script_res.message, "summary": script_res.message,
                        })
                else:
                    # 话术失败：明确错误，不伪造（仍走最终汇总说明失败）
                    yield _event("tool_result", {
                        "tool": "generate_sales_script", "ok": False,
                        "error_type": script_res.error_type, "message": script_res.message,
                    })

            # ---- Step 5: Compliance（最终校验）----
            script_texts = [
                s.get("content", "") for s in (tool_results.get("generate_sales_script") or {}).get("scripts", [])
            ]
            if script_texts:
                combined = "\n\n".join(script_texts)
                yield _event("tool_planned", {"tool": "check_compliance", "action": "正在执行最终合规检查"})
                yield _event("tool_start", {"tool": "check_compliance"})
                comp_res = await self.registry.execute(
                    "check_compliance", user=user, db=self.db,
                    args={"text": combined[:8000]}, context=context,
                )
                self._check_budget(tool_sequence, "check_compliance")
                tool_sequence.append("check_compliance")
                if comp_res.ok:
                    compliance_result = comp_res.data
                    yield _event("compliance", compliance_result)
                    yield _event("tool_result", {
                        "tool": "check_compliance", "ok": True,
                        "message": comp_res.message, "summary": f"合规：{compliance_result.get('status')}",
                    })
                else:
                    yield _event("tool_result", {
                        "tool": "check_compliance", "ok": False,
                        "error_type": comp_res.error_type, "message": comp_res.message,
                    })

            # ---- Step 6: LLM 汇总（安全：仅工具结果摘要）----
            async for ev in self._summarize(
                session=session, message=message,
                tool_results=tool_results, rag_status=rag_status,
                citations=citations, compliance=compliance_result,
                request_id=request_id,
            ):
                if isinstance(ev, str):
                    yield ev
                else:
                    final_message = ev

        except AgentLoopError as e:
            status = "error"
            final_message = str(e)
            yield _event("error", {"message": final_message, "error_type": "AGENT_LOOP"})
        except AgentBudgetError as e:
            status = "error"
            final_message = str(e)
            yield _event("error", {"message": final_message, "error_type": "AGENT_BUDGET"})
        except Exception as e:  # noqa: BLE001 —— 统一错误模型
            logger.error("sales_agent_error", request_id=request_id, error=str(e))
            status = "error"
            final_message = "销售助手暂时不可用，请稍后重试。"
            yield _event("error", {"message": final_message, "error_type": "INTERNAL"})

        latency_ms = int((time.perf_counter() - t0) * 1000)
        yield _event("agent_complete", {
            "request_id": request_id,
            "session_id": session.session_id,
            "status": status,
            "message": final_message,
            "tool_sequence": tool_sequence,
            "rag_status": rag_status,
            "citations": citations,
            "compliance": compliance_result,
            "latency_ms": latency_ms,
        })

        # 会话记忆（仅摘要，不含敏感/推理内容）
        self._remember(session, "user", message)
        self._remember(session, "assistant", final_message)
        logger.info(
            "sales_agent_completed",
            request_id=request_id, user_id=str(user.id),
            session_id=session.session_id, status=status,
            tool_sequence=tool_sequence, rag_status=rag_status,
            latency_ms=latency_ms, provider=settings.effective_ai_provider,
        )

    # ------------------------------------------------------------------
    # LLM 汇总（不泄露 CoT / 内部 prompt）
    # ------------------------------------------------------------------

    async def _summarize(
        self, session: AgentSession, message: str,
        tool_results: dict[str, Any], rag_status: str,
        citations: list[dict], compliance: dict | None,
        request_id: str,
    ) -> AsyncGenerator[str, None]:
        """基于工具结果生成最终回复（流式 message_delta）。

        yield str → SSE 事件 JSON；yield 最终消息文本（非 str）标记结束。
        """
        from app.ai.gateway import get_ai_gateway

        summary_parts: list[str] = []
        if tool_results.get("get_customer_context"):
            c = tool_results["get_customer_context"].get("customer") or {}
            summary_parts.append(
                f"客户：{c.get('name', '未知')}（类型 {c.get('customer_type', '未知')}，"
                f"阶段 {c.get('stage', '未知')}，意向 {c.get('intention_level', '未知')}）"
            )
        if tool_results.get("get_customer_activity"):
            a = tool_results["get_customer_activity"]
            summary_parts.append(
                f"沟通历史：互动 {a.get('interactions_count', 0)} 条，待办跟进 {len(a.get('pending_followups') or [])} 条"
            )
        if rag_status != "UNKNOWN" and rag_status != "REFUSE":
            summary_parts.append(f"RAG 状态：{rag_status}，依据 {len(citations)} 条")
        elif rag_status == "REFUSE":
            summary_parts.append("RAG 状态：REFUSE（知识库无充分产品依据）")

        scripts = (tool_results.get("generate_sales_script") or {}).get("scripts") or []
        if scripts:
            for s in scripts[:3]:
                summary_parts.append(
                    f"话术[{s.get('style_name')}]（合规 {((s.get('compliance') or {}).get('status'))}）：\n{s.get('content', '')[:2000]}"
                )
        elif rag_status == "REFUSE":
            summary_parts.append(_REFUSE_RAG_TEXT)

        summary_text = "\n\n".join(summary_parts)[:MAX_SUMMARY_CHARS]

        system_prompt = (
            "你是「安诊保 AI 副驾」的销售助手。请基于给定的工具结果，为用户生成一段面向"
            "客户沟通场景的中文回复（可包含给销售人员的行动建议）。\n"
            "要求：\n"
            "1. 只基于提供的工具结果陈述事实，禁止编造产品条款、保费、理赔条件\n"
            "2. 若 RAG 状态为 REFUSE，明确说明当前知识库无充分产品依据、建议咨询产品部门，禁止虚构产品内容\n"
            "3. 若合规状态为 RED，明确标注该内容不可直接用于客户，需修改后再使用\n"
            "4. 禁止收益承诺、绝对化表述、夸大保障、核保/理赔承诺\n"
            "5. 语言自然、专业、简洁\n"
            "6. 直接输出回复内容本身，不要输出任何思考过程或解释"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"客户诉求/背景：{message[:500]}\n\n--- 工具结果摘要 ---\n{summary_text}"
            )},
        ]

        gateway = get_ai_gateway()
        full = ""
        try:
            stream = await gateway.chat(messages=messages, stream=True, temperature=0.3)
            async for token in stream:
                full += token
                yield _event("message_delta", {"content": token})
        except Exception as e:  # noqa: BLE001
            logger.error("sales_agent_summarize_error", request_id=request_id, error=str(e))
            full = (
                "已为您完成客户分析与话术准备（详见上方工具结果）。"
                "AI 汇总服务暂不可用，请稍后重试。"
            )
            yield _event("message_delta", {"content": full})

        if not full.strip():
            full = "已完成分析，但未能生成汇总文本，请查看上方工具结果。"
            yield _event("message_delta", {"content": full})
        yield full.strip()


def _default_style(sales_stage: str | None) -> str | None:
    """根据销售阶段选择默认话术风格。"""
    if sales_stage == "initial_contact":
        return "affinity"
    if sales_stage in ("proposal", "negotiation", "closing"):
        return "professional"
    return None  # 默认生成全部风格（ScriptService 行为）


class AgentLoopError(Exception):
    """工具循环超限。"""


class AgentBudgetError(Exception):
    """工具调用预算超限。"""
