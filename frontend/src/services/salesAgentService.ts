import { useAuthStore } from '../stores/authStore';

// ---- Task 27 Agent SSE 事件类型 ----
export interface CitationItem {
  document_id?: string;
  document_title?: string;
  section?: string;
  source?: string;
  score?: number;
}

export interface ComplianceResult {
  status: 'GREEN' | 'YELLOW' | 'RED';
  score: number;
  issues: Array<{
    rule: string;
    severity: string;
    matched_text?: string;
    suggestion?: string;
  }>;
}

export interface AgentToolResultData {
  tool: string;
  ok: boolean;
  error_type?: string;
  message?: string;
  duration_ms?: number;
  summary?: string;
}

export type AgentEventType =
  | 'agent_start'
  | 'tool_planned'
  | 'tool_start'
  | 'tool_result'
  | 'rag_context'
  | 'message_delta'
  | 'compliance'
  | 'agent_complete'
  | 'error';

export interface AgentEvent {
  event: AgentEventType;
  data: Record<string, unknown>;
}

export interface AgentCompleteData {
  request_id?: string;
  session_id?: string;
  status: 'completed' | 'refused' | 'error';
  message?: string;
  tool_sequence?: string[];
  rag_status?: string;
  citations?: CitationItem[];
  compliance?: ComplianceResult | null;
  reason?: string;
  latency_ms?: number;
}

/** HTTP 错误（含后端语义码），用于 401/403/404 处理 */
export class AgentHttpError extends Error {
  status: number;
  detailMessage?: string;
  constructor(status: number, message: string, detailMessage?: string) {
    super(message);
    this.status = status;
    this.detailMessage = detailMessage;
  }
}

/**
 * 调用 AI Sales Agent SSE 端点（POST /api/v1/ai/sales-agent/chat）。
 * 返回 AsyncGenerator，每次 yield 一个 {event, data}。
 * 支持 AbortSignal 中止当前流。
 */
export async function* streamSalesAgentChat(
  customerId: string,
  message: string,
  opts?: {
    productType?: string;
    salesStage?: string;
    sessionId?: string;
    signal?: AbortSignal;
  }
): AsyncGenerator<AgentEvent> {
  const token = useAuthStore.getState().token;
  const baseUrl = '/api/v1';

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/ai/sales-agent/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({
        customer_id: customerId,
        message,
        product_type: opts?.productType || undefined,
        sales_stage: opts?.salesStage || undefined,
        session_id: opts?.sessionId || undefined,
      }),
      signal: opts?.signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') {
      throw new AgentHttpError(0, '已中止');
    }
    throw new Error('网络异常，请检查连接后重试。');
  }

  if (!response.ok) {
    // 解析后端 ErrorResponse / HTTPException detail 以展示真实语义
    let detailMessage: string | undefined;
    try {
      const body = await response.json();
      detailMessage =
        (body as { detail?: { message?: string } }).detail?.message ||
        (body as { error?: { message?: string } }).error?.message ||
        undefined;
    } catch {
      // 非 JSON 错误体，忽略
    }
    if (response.status === 401) {
      throw new AgentHttpError(401, '登录已过期，请重新登录。', detailMessage);
    }
    if (response.status === 403) {
      throw new AgentHttpError(403, '您没有权限执行该操作。', detailMessage);
    }
    if (response.status === 404) {
      throw new AgentHttpError(404, '客户不存在或无权访问。', detailMessage);
    }
    throw new AgentHttpError(
      response.status,
      detailMessage || `服务异常（HTTP ${response.status}）`,
      detailMessage
    );
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE 格式: "data: {json}\n\n"
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const parsed = JSON.parse(line.slice(6)) as AgentEvent;
          yield parsed;
        } catch {
          // 忽略 malformed JSON
        }
      }
    }
  }
}
