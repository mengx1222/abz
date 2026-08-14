import api from './api';
import { useAuthStore } from '../stores/authStore';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: Array<{
    title: string;
    chunk_id: string;
    relevance_score: number;
  }>;
  timestamp: Date;
  isLoading?: boolean;
}

export interface ConversationInfo {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

/**
 * 发送产品问答请求，通过 SSE 接收流式响应。
 * 返回一个 AsyncGenerator，每次 yield 一个 SSE 事件对象。
 */
export async function* streamProductQa(
  question: string,
  conversationId?: string,
): AsyncGenerator<{ event: string; data: Record<string, unknown> }> {
  const token = useAuthStore.getState().token;
  const baseUrl = '/api/v1';

  const response = await fetch(`${baseUrl}/ai/product-qa/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : '',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
    }),
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

    // Parse SSE: format is "data: {json}\n\n"
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
      // Handle "event: xxx" lines (we get event type from data payload)
    }
  }
}

/**
 * 获取会话列表
 */
export async function getConversations(): Promise<ConversationInfo[]> {
  const res = await api.get<{ success: boolean; data: ConversationInfo[] }>(
    '/ai/product-qa/conversations'
  );
  return res.data.data || [];
}
