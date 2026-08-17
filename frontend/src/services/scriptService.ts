import api from './api';
import { useAuthStore } from '../stores/authStore';

// ---- Types ----

export interface CustomerContext {
  name: string;
  age?: number | null;
  customer_type?: string | null;
  stage?: string | null;
  objection?: string | null;
  product_type?: string | null;
  insurance_knowledge?: string | null;
}

export interface ComplianceIssue {
  rule: string;
  severity: string;
  matched_text: string;
  suggestion: string;
}

export interface ComplianceResult {
  status: 'GREEN' | 'YELLOW' | 'RED' | string;
  score: number;
  issues: ComplianceIssue[];
}

/** RAG 知识依据（SSE rag_context / style_complete 的 citations 字段）。 */
export interface ScriptCitation {
  document_id: string;
  document_title: string;
  section?: string;
  source?: string;
  score?: number;
}

export interface Script {
  id: string;
  title: string;
  style: string;
  product_type: string | null;
  compliance_status: string;
  status: string;
  favorited_count: number;
  usage_count: number;
  created_at: string;
  updated_at: string;
  customer_context: CustomerContext | null;
  content?: string | null;
  compliance_issues?: ComplianceResult | null;
  version?: number;
}

export interface ScriptGenerateParams {
  customer_context: CustomerContext;
  style?: string | null;
  product_type?: string | null;
}

export interface ScriptFilters {
  style?: string | null;
  product_type?: string | null;
  compliance_status?: string | null;
  status?: string | null;
  search?: string | null;
}

// ---- SSE Events ----

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

/**
 * SSE流式话术生成。
 * 返回 AsyncGenerator，每次 yield 一个 SSE 事件对象。
 */
export async function* streamScriptGenerate(
  params: ScriptGenerateParams,
): AsyncGenerator<SSEEvent> {
  const token = useAuthStore.getState().token;
  const baseUrl = '/api/v1';

  const response = await fetch(`${baseUrl}/scripts/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : '',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const jsonStr = line.slice(6);
          const parsed = JSON.parse(jsonStr);
          yield parsed;
        } catch {
          // Ignore malformed JSON
        }
      }
    }
  }
}

/**
 * 获取话术列表
 */
export async function getScripts(filters?: ScriptFilters): Promise<Script[]> {
  const params: Record<string, string> = {};
  if (filters?.style) params.style = filters.style;
  if (filters?.product_type) params.product_type = filters.product_type;
  if (filters?.compliance_status) params.compliance_status = filters.compliance_status;
  if (filters?.status) params.status = filters.status;
  if (filters?.search) params.search = filters.search;

  const res = await api.get<{ success: boolean; data: Script[] }>(
    '/scripts',
    { params },
  );
  return res.data.data || [];
}

/**
 * 获取话术详情
 */
export async function getScript(scriptId: string): Promise<Script> {
  const res = await api.get<{ success: boolean; data: Script }>(
    `/scripts/${scriptId}`,
  );
  return res.data.data;
}

/**
 * 收藏话术
 */
export async function toggleFavorite(scriptId: string): Promise<Script> {
  const res = await api.post<{ success: boolean; data: Script }>(
    `/scripts/${scriptId}/favorite`,
  );
  return res.data.data;
}

/**
 * 删除话术
 */
export async function deleteScript(scriptId: string): Promise<void> {
  await api.delete(`/scripts/${scriptId}`);
}

/**
 * 合规检查
 */
export async function checkCompliance(text: string): Promise<ComplianceResult> {
  const res = await api.post<{ success: boolean; data: ComplianceResult }>(
    '/scripts/check-compliance',
    { text },
  );
  return res.data.data;
}
