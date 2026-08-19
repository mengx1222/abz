"""AI Sales Agent —— 白名单工具实现。

每个工具复用现有 Service / RAG Pipeline / Compliance，不重实现业务能力：
- get_customer_context     → CustomerService.get_customer（含 IDOR 防护）
- get_customer_activity    → 同一 Customer 详情的 interactions/followups 摘要
- search_product_knowledge → RAGPipeline.query + Confidence Gate + Citation
- generate_sales_script    → ScriptService.generate_scripts（RAG+Confidence+Compliance+持久化）
- check_compliance         → compliance_service.check_compliance

隐私底线：发送给 Provider / 输出到前端的客户字段为最小化集合，
绝不包含 phone / notes / 身份证 / 银行卡等无关敏感字段。
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from structlog import get_logger

from app.agent.registry import (
    ERROR_INVALID_ARGS,
    ERROR_NOT_FOUND,
    ERROR_PERMISSION_DENIED,
    ToolContract,
    ToolResult,
)

logger = get_logger()

# 发送给模型的最小化客户字段白名单（隐私：不含 phone/notes/身份证等）
_CUSTOMER_MINIMAL_FIELDS = (
    "id", "name", "age", "gender", "customer_type", "stage",
    "intention_level", "product_type", "tags", "organization_id",
)


def _normalize_customer_minimal(raw: dict[str, Any]) -> dict[str, Any]:
    """将 customer dict 规范化为最小化上下文（兼容 demo/production 字段差异）。"""
    stage = raw.get("current_stage") or raw.get("stage")
    product_type = raw.get("insurance_type") or raw.get("product_type")
    out: dict[str, Any] = {}
    for key in _CUSTOMER_MINIMAL_FIELDS:
        if key == "stage":
            if stage:
                out[key] = stage
        elif key == "product_type":
            if product_type:
                out[key] = product_type
        elif raw.get(key) is not None:
            out[key] = raw.get(key)
    return out


# ----------------------------------------------------------------------
# 1. get_customer_context
# ----------------------------------------------------------------------

async def _tool_get_customer_context(
    user: Any, db: Any, args: dict[str, Any], context: dict[str, Any],
) -> ToolResult:
    """读取已有 Customer 数据并输出最小化上下文（复用 CustomerService 的 IDOR 防护）。"""
    customer_id_str = (args.get("customer_id") or "").strip()
    if not customer_id_str:
        return ToolResult(
            tool="get_customer_context", ok=False, error_type=ERROR_INVALID_ARGS,
            message="customer_id 必填",
        )
    try:
        customer_id = uuid.UUID(customer_id_str)
    except ValueError:
        return ToolResult(
            tool="get_customer_context", ok=False, error_type=ERROR_INVALID_ARGS,
            message=f"customer_id 非法: {customer_id_str}",
        )

    from app.services.customer_service import CustomerService

    service = CustomerService(session=db)
    customer = await service.get_customer(customer_id, current_user=user)
    if customer is None:
        return ToolResult(
            tool="get_customer_context", ok=False, error_type=ERROR_NOT_FOUND,
            message="客户不存在或无权访问（组织范围外）",
        )

    minimal = _normalize_customer_minimal(customer)
    return ToolResult(
        tool="get_customer_context", ok=True,
        data={"customer": minimal},
        message=f"已获取客户 {minimal.get('name', customer_id_str)} 的上下文",
    )


# ----------------------------------------------------------------------
# 2. get_customer_activity
# ----------------------------------------------------------------------

async def _tool_get_customer_activity(
    user: Any, db: Any, args: dict[str, Any], context: dict[str, Any],
) -> ToolResult:
    """读取客户互动/跟进历史摘要（复用 CustomerService，不重建 CRM）。"""
    customer_id_str = (args.get("customer_id") or "").strip()
    if not customer_id_str:
        return ToolResult(
            tool="get_customer_activity", ok=False, error_type=ERROR_INVALID_ARGS,
            message="customer_id 必填",
        )
    try:
        customer_id = uuid.UUID(customer_id_str)
    except ValueError:
        return ToolResult(
            tool="get_customer_activity", ok=False, error_type=ERROR_INVALID_ARGS,
            message=f"customer_id 非法: {customer_id_str}",
        )

    from app.services.customer_service import CustomerService

    service = CustomerService(session=db)
    customer = await service.get_customer(customer_id, current_user=user)
    if customer is None:
        return ToolResult(
            tool="get_customer_activity", ok=False, error_type=ERROR_NOT_FOUND,
            message="客户不存在或无权访问（组织范围外）",
        )

    interactions = customer.get("interactions") or []
    followups = customer.get("followups") or []
    latest = []
    for i in sorted(interactions, key=lambda x: x.get("created_at") or "", reverse=True)[:3]:
        latest.append({
            "type": i.get("type"),
            "direction": i.get("direction"),
            "summary": (i.get("content") or "")[:120],
            "outcome": i.get("outcome"),
            "created_at": i.get("created_at"),
        })
    return ToolResult(
        tool="get_customer_activity", ok=True,
        data={
            "customer_id": customer_id_str,
            "interactions_count": len(interactions),
            "followups_count": len(followups),
            "latest_interactions": latest,
            "pending_followups": [
                {"scheduled_date": f.get("scheduled_date"), "status": f.get("status")}
                for f in followups
                if f.get("status") not in ("completed", "cancelled")
            ][:5],
        },
        message=f"已获取客户活动摘要（互动 {len(interactions)} 条 / 跟进 {len(followups)} 条）",
    )


# ----------------------------------------------------------------------
# 3. search_product_knowledge
# ----------------------------------------------------------------------

async def _tool_search_product_knowledge(
    user: Any, db: Any, args: dict[str, Any], context: dict[str, Any],
) -> ToolResult:
    """调用现有生产 RAG（Vector+BM25+RRF+Product Boundary+Role/Org 权限+Confidence+Citation）。

    rag_status ∈ ALLOW / REVIEW / REFUSE / ERROR：
    - REFUSE 时 Agent 不得调用模型编造产品条款，必须把拒答状态结构化返回
    - citations 进入最终 Agent result 供前端展示
    """
    question = (args.get("question") or "").strip()
    product_type = (args.get("product_type") or "").strip()
    if not question or not product_type:
        return ToolResult(
            tool="search_product_knowledge", ok=False, error_type=ERROR_INVALID_ARGS,
            message="question 与 product_type 必填",
        )

    from app.agent.tools_common import _build_rag_permission_context
    from app.rag.pipeline import RAGPipeline
    from app.rag.safety import assess_confidence, should_refuse_answer

    pipeline = RAGPipeline(db=db)
    perm = await _build_rag_permission_context(user, db)

    try:
        search_results, context_text = await pipeline.query(
            question=question,
            top_k=6,
            product_type=product_type,
            user_roles=perm["roles"],
            org_id=perm["org_id"],
            accessible_org_ids=perm["accessible_org_ids"],
        )
    except Exception as e:  # noqa: BLE001 —— 统一错误模型
        logger.error("agent_rag_search_error", error=str(e))
        return ToolResult(
            tool="search_product_knowledge", ok=False,
            error_type="PROVIDER_ERROR",
            message="知识库检索暂不可用，未使用产品知识依据",
            data={"rag_status": "ERROR", "citations": [], "product_type": product_type},
        )

    refuse, top_score, count = should_refuse_answer(search_results)
    confidence = assess_confidence(search_results)
    if refuse or confidence.level in ("NONE", "LOW"):
        rag_status = "REFUSE"
        citations: list[dict] = []
    else:
        rag_status = "ALLOW" if confidence.level == "HIGH" else "REVIEW"
        citations = [
            {
                "document_id": r.document_id,
                "document_title": r.document_title,
                "section": r.metadata.get("heading", ""),
                "source": r.content[:300],
                "score": round(r.score, 3),
            }
            for r in search_results[:3]
        ]

    return ToolResult(
        tool="search_product_knowledge", ok=True,
        data={
            "rag_status": rag_status,
            "product_type": product_type,
            "confidence": confidence.level.value if hasattr(confidence.level, "value") else str(confidence.level),
            "top_score": round(top_score, 3),
            "sources_count": count,
            "context_length": len(context_text),
            "citations": citations,
        },
        message=f"RAG 检索完成: {rag_status}（来源 {count} 条）",
    )


# ----------------------------------------------------------------------
# 4. generate_sales_script
# ----------------------------------------------------------------------

async def _tool_generate_sales_script(
    user: Any, db: Any, args: dict[str, Any], context: dict[str, Any],
) -> ToolResult:
    """调用现有 Script Production 逻辑（RAG+Confidence Gate+Compliance+持久化）。

    消费 ScriptService.generate_scripts 的 SSE 事件流，汇总最终话术与合规状态。
    RAG REFUSE 时 ScriptService 返回 style_refused（不生成产品事实话术），原样透传。
    """
    style = (args.get("style") or "").strip() or None
    product_type = (args.get("product_type") or "").strip() or None
    customer_context = args.get("customer_context") or context.get("customer") or {}
    if not isinstance(customer_context, dict) or not customer_context:
        return ToolResult(
            tool="generate_sales_script", ok=False, error_type=ERROR_INVALID_ARGS,
            message="customer_context 必填（请先调用 get_customer_context）",
        )

    from app.services.script_service import ScriptService

    service = ScriptService(session=db)
    scripts: list[dict] = []
    rag_status = "UNKNOWN"
    citations: list[dict] = []
    refused: list[str] = []
    errors: list[str] = []

    try:
        async for event_json in service.generate_scripts(
            customer_context=customer_context,
            style=style,
            product_type=product_type,
            user_id=str(user.id),
        ):
            event = json.loads(event_json)
            etype, edata = event.get("event"), event.get("data") or {}
            if etype == "rag_context":
                rag_status = edata.get("status", rag_status)
                citations = edata.get("citations") or citations
            elif etype == "style_complete":
                scripts.append({
                    "style": edata.get("style"),
                    "style_name": edata.get("style_name"),
                    "content": edata.get("content", ""),
                    "compliance": edata.get("compliance"),
                    "word_count": edata.get("word_count"),
                })
            elif etype == "style_refused":
                refused.append(edata.get("style") or "?")
            elif etype == "style_error":
                errors.append(edata.get("message") or "话术生成失败")
    except PermissionError:
        return ToolResult(
            tool="generate_sales_script", ok=False, error_type=ERROR_PERMISSION_DENIED,
            message="无权生成话术",
        )
    except Exception as e:  # noqa: BLE001 —— 统一错误模型
        logger.error("agent_script_tool_error", error=str(e))
        return ToolResult(
            tool="generate_sales_script", ok=False, error_type="PROVIDER_ERROR",
            message="话术生成服务不可用，请稍后重试",
        )

    if not scripts and refused:
        # 全部拒答（RAG 无依据）——结构化透传 REFUSE，不编造
        return ToolResult(
            tool="generate_sales_script", ok=True,
            data={
                "rag_status": rag_status or "REFUSE",
                "scripts": [],
                "refused_styles": refused,
                "citations": citations,
            },
            message=f"知识库无充分产品依据，话术已拒答（{len(refused)} 个风格），未生成产品事实内容",
        )
    if not scripts and errors:
        return ToolResult(
            tool="generate_sales_script", ok=False, error_type="PROVIDER_ERROR",
            message="；".join(errors[:2]),
        )

    worst = "GREEN"
    for s in scripts:
        st = (s.get("compliance") or {}).get("status")
        if st == "RED":
            worst = "RED"
        elif st == "YELLOW" and worst != "RED":
            worst = "YELLOW"
    return ToolResult(
        tool="generate_sales_script", ok=True,
        data={
            "rag_status": rag_status,
            "scripts": scripts,
            "citations": citations,
            "refused_styles": refused,
            "compliance_status": worst,
        },
        message=f"已生成 {len(scripts)} 条话术（合规 {worst}）",
    )


# ----------------------------------------------------------------------
# 5. check_compliance
# ----------------------------------------------------------------------

async def _tool_check_compliance(
    user: Any, db: Any, args: dict[str, Any], context: dict[str, Any],
) -> ToolResult:
    """调用现有 Compliance Engine 检查文本。RED 阻止标记可用，YELLOW 需人工确认。"""
    text = (args.get("text") or "").strip()
    if not text:
        return ToolResult(
            tool="check_compliance", ok=False, error_type=ERROR_INVALID_ARGS,
            message="text 必填",
        )

    from app.services.compliance_service import check_compliance

    result = check_compliance(text)
    return ToolResult(
        tool="check_compliance", ok=True,
        data=result,
        message=f"合规检查: {result['status']}（score {result['score']}，问题 {len(result['issues'])} 条）",
    )


# ----------------------------------------------------------------------
# 注册表构建
# ----------------------------------------------------------------------

def build_default_registry() -> Any:
    """构建默认 ToolRegistry（白名单）。"""
    from app.agent.registry import ToolRegistry

    registry = ToolRegistry()
    registry.register(ToolContract(
        name="get_customer_context",
        description="读取客户基础上下文（最小化字段），用于理解销售对象",
        input_schema={"type": "object", "required": ["customer_id"], "properties": {"customer_id": {"type": "string"}}},
        handler=_tool_get_customer_context,
        required_permission="customer:read",
        timeout_seconds=15.0,
    ))
    registry.register(ToolContract(
        name="get_customer_activity",
        description="读取客户互动/跟进历史摘要",
        input_schema={"type": "object", "required": ["customer_id"], "properties": {"customer_id": {"type": "string"}}},
        handler=_tool_get_customer_activity,
        required_permission="customer:read",
        timeout_seconds=15.0,
    ))
    registry.register(ToolContract(
        name="search_product_knowledge",
        description="检索产品知识库（RAG），返回依据与引用；REFUSE 表示无合法依据",
        input_schema={
            "type": "object",
            "required": ["question", "product_type"],
            "properties": {"question": {"type": "string"}, "product_type": {"type": "string"}},
        },
        handler=_tool_search_product_knowledge,
        required_permission="rag:query",
        timeout_seconds=30.0,
    ))
    registry.register(ToolContract(
        name="generate_sales_script",
        description="生成销售话术（RAG 依据 + 合规检查 + 持久化），输出话术与合规状态",
        input_schema={
            "type": "object",
            "required": ["customer_context"],
            "properties": {
                "customer_context": {"type": "object"},
                "style": {"type": "string"},
                "product_type": {"type": "string"},
            },
        },
        handler=_tool_generate_sales_script,
        required_permission="script:generate",
        timeout_seconds=60.0,
    ))
    registry.register(ToolContract(
        name="check_compliance",
        description="对任意文本执行合规检查（RED 阻止 / YELLOW 人工确认 / GREEN 通过）",
        input_schema={"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
        handler=_tool_check_compliance,
        required_permission=None,
        timeout_seconds=5.0,
    ))
    return registry
