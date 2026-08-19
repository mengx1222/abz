"""AI Sales Agent —— Tool Registry / Tool Contract。

每个工具定义清晰的名称、描述、输入 schema、输出 schema、权限要求、超时、错误类型。
Agent 只允许调用注册表中的工具；工具只能调用白名单内的内部 Service。
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from structlog import get_logger

logger = get_logger()

# 确定的错误类型（错误模型，禁止 silent fallback）
ERROR_PERMISSION_DENIED = "PERMISSION_DENIED"
ERROR_NOT_FOUND = "NOT_FOUND"
ERROR_TOOL_TIMEOUT = "TOOL_TIMEOUT"
ERROR_PROVIDER_ERROR = "PROVIDER_ERROR"
ERROR_INVALID_ARGS = "INVALID_ARGS"
ERROR_INTERNAL = "INTERNAL"

ALL_ERROR_TYPES = (
    ERROR_PERMISSION_DENIED,
    ERROR_NOT_FOUND,
    ERROR_TOOL_TIMEOUT,
    ERROR_PROVIDER_ERROR,
    ERROR_INVALID_ARGS,
    ERROR_INTERNAL,
)


@dataclass
class ToolResult:
    """工具执行结果 —— 统一的成功/失败结构。

    - ok=True: data 为业务结果（结构化 dict）
    - ok=False: error_type 必须为 ALL_ERROR_TYPES 之一，message 为人类可读拒绝/失败说明
    - 无权限调用必须返回明确的拒绝结果（PERMISSION_DENIED），不是空白/fallback
    """

    tool: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    message: str = ""
    duration_ms: int = 0


@dataclass
class ToolContract:
    """工具契约。"""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Awaitable[ToolResult]]
    required_permission: str | None = None
    timeout_seconds: float = 20.0
    error_types: tuple[str, ...] = ALL_ERROR_TYPES


class ToolRegistry:
    """工具注册表 —— Agent 可调用工具的白名单。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolContract] = {}

    def register(self, contract: ToolContract) -> None:
        if contract.name in self._tools:
            raise ValueError(f"tool already registered: {contract.name}")
        self._tools[contract.name] = contract

    def get(self, name: str) -> ToolContract | None:
        return self._tools.get(name)

    def list(self) -> list[ToolContract]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    async def execute(
        self,
        name: str,
        *,
        user: Any,
        db: Any,
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolResult:
        """执行工具（含超时与错误归一化）。

        错误模型：
        - 工具超时 → TOOL_TIMEOUT
        - 工具内部抛 PermissionError → PERMISSION_DENIED
        - 工具内部抛 LookupError/ValueError → NOT_FOUND / INVALID_ARGS
        - 其余异常 → INTERNAL（生产模式绝不 fallback 到 Mock 或业务默认值）
        """
        contract = self.get(name)
        if contract is None:
            return ToolResult(
                tool=name,
                ok=False,
                error_type=ERROR_INVALID_ARGS,
                message=f"unknown tool: {name}（Agent 仅允许调用白名单内工具）",
            )

        t0 = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                contract.handler(user=user, db=db, args=args, context=context),
                timeout=contract.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("agent_tool_timeout", tool=name, timeout=contract.timeout_seconds)
            return ToolResult(
                tool=name,
                ok=False,
                error_type=ERROR_TOOL_TIMEOUT,
                message=f"工具 {name} 执行超时（>{contract.timeout_seconds}s）",
            )
        except PermissionError as e:
            return ToolResult(
                tool=name,
                ok=False,
                error_type=ERROR_PERMISSION_DENIED,
                message=str(e) or f"无权执行 {name}",
            )
        except LookupError as e:
            return ToolResult(
                tool=name,
                ok=False,
                error_type=ERROR_NOT_FOUND,
                message=str(e) or f"未找到资源",
            )
        except ValueError as e:
            return ToolResult(
                tool=name,
                ok=False,
                error_type=ERROR_INVALID_ARGS,
                message=str(e) or f"工具 {name} 参数无效",
            )
        except Exception as e:  # noqa: BLE001 —— 统一错误模型
            logger.error("agent_tool_internal_error", tool=name, error=str(e))
            return ToolResult(
                tool=name,
                ok=False,
                error_type=ERROR_INTERNAL,
                message=f"工具 {name} 内部错误",
            )

        result.duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "agent_tool_executed",
            tool=name,
            ok=result.ok,
            error_type=result.error_type,
            duration_ms=result.duration_ms,
        )
        return result
