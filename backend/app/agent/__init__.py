"""AI Sales Agent —— 后端编排核心（第一阶段）。

架构: API/Router → SalesAgentService(Orchestrator) → ToolRegistry → Existing Services → AI Gateway → SSE

原则:
- 工具是 Agent 调用现有业务能力的唯一入口（白名单），禁止 LLM 自由生成函数名/URL
- 所有工具复用现有 Service/Repository/RAG/Compliance，不重实现业务能力
- 所有工具携带当前 User，由底层 Service 再次执行 RBAC / Organization Scope 检查
- Agent 不直接访问 ORM 做业务查询、不直接调用 Provider SDK、不自己实现权限过滤
"""
