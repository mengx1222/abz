import api from './api';
import { useAuthStore } from '../stores/authStore';

// ---- Types ----

export interface CustomerPersona {
  name: string;
  age: number;
  personality: string;
  mood: string;
  background: string;
  insurance_knowledge: string;
  key_objections: string[];
}

export interface Scenario {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  product_focus: string | null;
  sales_stage: string | null;
  duration_minutes: number;
  customer_persona: CustomerPersona;
  category: string;
  evaluation_criteria?: Record<string, unknown>;
}

export interface TrainingSession {
  id: string;
  scenario_id: string | null;
  scenario_title: string | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  message_count: number;
  total_score: number | null;
  messages?: TrainingMessage[];
}

export interface TrainingMessage {
  id: string;
  role: 'agent' | 'customer' | 'coach';
  content: string;
  created_at: string;
  score?: number | null;
  coaching_hint?: { hint: string; category: string } | null;
}

export interface TrainingScore {
  total_score: number;
  product_accuracy: number;
  empathy: number;
  closing_action: number;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}

export interface TrainingStats {
  total_sessions: number;
  completed_sessions: number;
  avg_score: number | null;
  avg_product_accuracy: number | null;
  avg_empathy: number | null;
  avg_closing_action: number | null;
  best_score: number | null;
  trend: Array<{ date: string; avg_score: number; session_count: number }>;
  difficulty_distribution: Record<string, number>;
  product_focus_distribution: Record<string, number>;
}

// ---- SSE Events ----

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

/**
 * SSE流式发送陪练消息。
 * 事件序列：message_start → token* → coaching → turn_complete
 */
export async function* streamTrainingMessage(
  sessionId: string,
  content: string,
): AsyncGenerator<SSEEvent> {
  const token = useAuthStore.getState().token;
  const baseUrl = '/api/v1';

  const response = await fetch(`${baseUrl}/training/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : '',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ content }),
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
          const parsed = JSON.parse(line.slice(6));
          yield parsed;
        } catch { /* ignore */ }
      }
    }
  }
}

/**
 * SSE流式完成训练评分。
 * 事件序列：scoring_start → token* → score_data → scoring_complete
 */
export async function* streamTrainingScore(
  sessionId: string,
): AsyncGenerator<SSEEvent> {
  const token = useAuthStore.getState().token;
  const baseUrl = '/api/v1';

  const response = await fetch(`${baseUrl}/training/sessions/${sessionId}/complete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : '',
      Accept: 'text/event-stream',
    },
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
          const parsed = JSON.parse(line.slice(6));
          yield parsed;
        } catch { /* ignore */ }
      }
    }
  }
}

/**
 * 获取训练场景列表
 */
export async function getScenarios(params?: {
  difficulty?: string | null;
  product_focus?: string | null;
}): Promise<Scenario[]> {
  const res = await api.get<{ success: boolean; data: Scenario[] }>(
    '/training/scenarios',
    { params },
  );
  return res.data.data || [];
}

/**
 * 获取场景详情
 */
export async function getScenario(scenarioId: string): Promise<Scenario> {
  const res = await api.get<{ success: boolean; data: Scenario }>(
    `/training/scenarios/${scenarioId}`,
  );
  return res.data.data;
}

/**
 * 开始训练会话
 */
export async function startSession(scenarioId: string): Promise<TrainingSession> {
  const res = await api.post<{ success: boolean; data: TrainingSession }>(
    '/training/sessions',
    { scenario_id: scenarioId },
  );
  return res.data.data;
}

/**
 * 获取训练会话列表
 */
export async function getSessions(): Promise<TrainingSession[]> {
  const res = await api.get<{ success: boolean; data: TrainingSession[] }>(
    '/training/sessions',
  );
  return res.data.data || [];
}

/**
 * 获取会话详情
 */
export async function getSession(sessionId: string): Promise<TrainingSession> {
  const res = await api.get<{ success: boolean; data: TrainingSession }>(
    `/training/sessions/${sessionId}`,
  );
  return res.data.data;
}

/**
 * 获取训练统计
 */
export async function getTrainingStats(): Promise<TrainingStats> {
  const res = await api.get<{ success: boolean; data: TrainingStats }>(
    '/training/stats',
  );
  return res.data.data;
}
