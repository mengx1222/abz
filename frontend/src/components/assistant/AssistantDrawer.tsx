import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Sparkles, X, RefreshCw, Search, UserRound } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { EmptyState } from '../ui/EmptyState';
import {
  AgentHttpError,
  streamSalesAgentChat,
  type AgentCompleteData,
  type AgentEvent,
  type CitationItem,
  type ComplianceResult,
} from '../../services/salesAgentService';
import { listCustomers, type Customer } from '../../services/customerService';
import { useAssistantStore } from '../../stores/assistantStore';
import {
  CompliancePanel,
  CitationPanel,
  ToolStatusLog,
  type AgentMessage,
} from './chatParts';

/** 会话持久化 key（刷新后恢复对话上下文；sessionId 由后端 Redis session 续接） */
const STORAGE_KEY = 'azb_ai_assistant_v1';

interface PersistedSession {
  customerId: string;
  customerName: string;
  insuranceType?: string | null;
  sessionId: string | null;
  messages: AgentMessage[];
}

function loadPersisted(): PersistedSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as PersistedSession;
    if (!data.customerId || !Array.isArray(data.messages)) return null;
    // 恢复时把中断在 streaming 的消息按内容落定，避免僵尸光标
    data.messages = data.messages
      .filter((m) => m.role === 'user' || m.content || m.status === 'error')
      .map((m) =>
        m.status === 'streaming'
          ? { ...m, status: m.content ? ('completed' as const) : ('error' as const), errorMessage: m.content ? undefined : '已中断。' }
          : m
      );
    return data;
  } catch {
    return null;
  }
}

function savePersisted(data: PersistedSession | null) {
  try {
    if (!data) sessionStorage.removeItem(STORAGE_KEY);
    else sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ ...data, messages: data.messages.slice(-40) }));
  } catch {
    // 存储不可用（隐私模式等）静默降级为内存会话
  }
}

interface SelectedCustomer {
  id: string;
  name: string;
  insurance_type?: string | null;
}

export function AssistantDrawer() {
  const open = useAssistantStore((s) => s.open);
  const setOpen = useAssistantStore((s) => s.setOpen);

  const [customer, setCustomer] = useState<SelectedCustomer | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  /** 首次打开时的恢复标记：持久化里已有客户则直接进入对话 */
  const [restored, setRestored] = useState(false);

  // ---- 客户选择器状态 ----
  const [keyword, setKeyword] = useState('');
  const [candidates, setCandidates] = useState<Customer[]>([]);
  const [pickerLoading, setPickerLoading] = useState(false);
  const [pickerError, setPickerError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ---- 挂载恢复（仅一次） ----
  useEffect(() => {
    const saved = loadPersisted();
    if (saved) {
      setCustomer({
        id: saved.customerId,
        name: saved.customerName,
        insurance_type: saved.insuranceType ?? null,
      });
      setSessionId(saved.sessionId ?? null);
      setMessages(saved.messages);
      setRestored(true);
    }
  }, []);

  // ---- 持久化 ----
  useEffect(() => {
    if (!restored && messages.length === 0 && !customer) return;
    savePersisted(
      customer
        ? {
            customerId: customer.id,
            customerName: customer.name,
            insuranceType: customer.insurance_type ?? null,
            sessionId,
            messages,
          }
        : null
    );
  }, [customer, sessionId, messages, restored]);

  // Esc 关闭
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, setOpen]);

  // 卸载时中止流
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (open) chatEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, open]);

  // 打开时聚焦输入框
  useEffect(() => {
    if (open && customer) setTimeout(() => inputRef.current?.focus(), 250);
  }, [open, customer]);

  // ---- 客户搜索（300ms 防抖） ----
  useEffect(() => {
    if (!open || customer) return;
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(async () => {
      setPickerLoading(true);
      setPickerError(null);
      try {
        const res = await listCustomers({ search: keyword.trim() || undefined, page_size: 20 });
        setCandidates(res.items);
      } catch {
        setPickerError('客户列表加载失败，请重试');
        setCandidates([]);
      } finally {
        setPickerLoading(false);
      }
    }, 300);
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [keyword, open, customer]);

  const patchAssistant = useCallback((id: string, patch: Partial<AgentMessage>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }, []);

  function handleEvent(id: string, event: AgentEvent) {
    const { event: type, data } = event;
    switch (type) {
      case 'agent_start': {
        if (typeof data.session_id === 'string') setSessionId(data.session_id);
        break;
      }
      case 'tool_planned': {
        const action = typeof data.action === 'string' ? data.action : '';
        if (action) {
          setMessages((prev) =>
            prev.map((m) => (m.id === id ? { ...m, toolLog: [...m.toolLog, action] } : m))
          );
        }
        break;
      }
      case 'rag_context': {
        const ragStatus = typeof data.status === 'string' ? data.status : null;
        const citations = Array.isArray(data.citations) ? (data.citations as CitationItem[]) : [];
        patchAssistant(id, { ragStatus, citations });
        break;
      }
      case 'message_delta': {
        if (typeof data.content === 'string' && data.content) {
          setMessages((prev) =>
            prev.map((m) => (m.id === id ? { ...m, content: m.content + data.content } : m))
          );
        }
        break;
      }
      case 'compliance': {
        patchAssistant(id, { compliance: data as unknown as ComplianceResult });
        break;
      }
      case 'agent_complete': {
        const complete = data as unknown as AgentCompleteData;
        const msg = typeof complete.message === 'string' ? complete.message : '';
        setMessages((prev) =>
          prev.map((m) =>
            m.id === id
              ? {
                  ...m,
                  status: complete.status === 'refused' ? 'refused' : 'completed',
                  content: msg || m.content,
                  citations:
                    Array.isArray(complete.citations) && complete.citations.length
                      ? complete.citations
                      : m.citations,
                  compliance:
                    (complete.compliance as ComplianceResult | null) ?? m.compliance ?? null,
                  ragStatus:
                    typeof complete.rag_status === 'string' ? complete.rag_status : m.ragStatus,
                }
              : m
          )
        );
        break;
      }
      case 'error': {
        patchAssistant(id, {
          status: 'error',
          errorMessage: typeof data.message === 'string' ? data.message : '服务异常，请稍后重试。',
        });
        break;
      }
      default:
        break;
    }
  }

  async function handleSend(text?: string) {
    const q = (text ?? input).trim();
    if (!q || isStreaming || !customer) return;

    setInput('');
    setIsStreaming(true);

    const userMsg: AgentMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: q,
      toolLog: [],
      citations: [],
      compliance: null,
      ragStatus: null,
      status: 'completed',
    };
    setMessages((prev) => [...prev, userMsg]);
    const assistantId = `assistant-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: 'assistant',
        content: '',
        toolLog: [],
        citations: [],
        compliance: null,
        ragStatus: null,
        status: 'streaming',
      },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const event of streamSalesAgentChat(customer.id, q, {
        productType: customer.insurance_type ?? undefined,
        sessionId: sessionId ?? undefined,
        signal: controller.signal,
      })) {
        handleEvent(assistantId, event);
      }
      // 流正常结束兜底
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId && m.status === 'streaming'
            ? {
                ...m,
                status: m.content ? 'completed' : 'error',
                errorMessage: m.content ? undefined : 'Agent 未返回结果，请重试。',
              }
            : m
        )
      );
    } catch (err) {
      if (err instanceof AgentHttpError && err.status === 0) {
        // 用户主动中止
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId && m.status === 'streaming'
              ? {
                  ...m,
                  status: m.content ? 'completed' : 'error',
                  errorMessage: m.content ? undefined : '已中止。',
                }
              : m
          )
        );
      } else if (err instanceof AgentHttpError) {
        patchAssistant(assistantId, {
          status: 'error',
          errorMessage:
            err.detailMessage ||
            (err.status === 401
              ? '登录已过期，请重新登录。'
              : err.status === 403 || err.status === 404
                ? '客户不存在或无权访问。'
                : `服务异常（HTTP ${err.status}）`),
        });
      } else {
        patchAssistant(assistantId, {
          status: 'error',
          errorMessage: (err as Error).message || '网络异常，请检查连接后重试。',
        });
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void handleSend();
  }

  function handleClearConversation() {
    abortRef.current?.abort();
    setMessages([]);
    setSessionId(null);
  }

  function handleChangeCustomer() {
    abortRef.current?.abort();
    setCustomer(null);
    setKeyword('');
    setCandidates([]);
    savePersisted(null);
  }

  function retry(message: AgentMessage) {
    const text = message.content || message.errorMessage || '';
    if (!text.trim()) return;
    void handleSend(text);
  }

  const canSend = !!customer && !isStreaming && input.trim().length > 0;

  if (!open) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-[400px] flex flex-col bg-card border-l border-border shadow-overlay animate-slide-in-right">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-5 h-16 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="flex items-center justify-center h-8 w-8 rounded-lg bg-accent/10 flex-shrink-0">
            <Sparkles className="h-4 w-4 text-accent" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-text leading-tight">AI 助手</p>
            <p className="text-[11px] text-muted leading-tight truncate">
              {customer ? `正在协助客户：${customer.name}` : '选择客户开始对话'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {customer && (
            <Button variant="ghost" size="sm" onClick={handleClearConversation} disabled={isStreaming}>
              清空
            </Button>
          )}
          <button
            onClick={() => setOpen(false)}
            aria-label="关闭助手"
            className="h-8 w-8 flex items-center justify-center rounded-md text-muted hover:text-text hover:bg-bg transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Body */}
      {!customer ? (
        /* ---- 客户选择器 ---- */
        <div className="flex-1 flex flex-col min-h-0">
          <div className="p-4 pb-2 flex-shrink-0">
            <Input
              type="text"
              placeholder="搜索客户姓名..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              icon={<Search className="w-4 h-4" />}
              autoFocus
            />
            <p className="text-xs text-muted mt-2">
              助手基于客户画像与产品知识库作答，请先指定一位客户。
            </p>
          </div>
          <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-1.5 min-h-0">
            {pickerLoading ? (
              <LoadingSpinner size="sm" className="py-10" />
            ) : pickerError ? (
              <EmptyState title={pickerError} />
            ) : candidates.length === 0 ? (
              <EmptyState icon={<UserRound className="h-5 w-5 text-muted" />} title="未找到匹配的客户" description="试试其他关键词，或到「客户360」新建客户。" />
            ) : (
              candidates.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() =>
                    setCustomer({
                      id: c.id,
                      name: c.name || '未知客户',
                      insurance_type: c.insurance_type ?? null,
                    })
                  }
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-border bg-card hover:border-accent/40 hover:bg-accent/5 transition-colors cursor-pointer text-left"
                >
                  <span className="flex-shrink-0 h-8 w-8 rounded-full bg-accent/10 text-accent text-xs font-semibold flex items-center justify-center">
                    {(c.name || '?').charAt(0)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-text truncate">{c.name}</span>
                    <span className="block text-xs text-muted truncate">
                      {[c.customer_type, c.current_stage].filter(Boolean).join(' · ') || '—'}
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      ) : (
        /* ---- 对话区 ---- */
        <>
          <div className="flex items-center justify-between gap-2 px-5 py-2 border-b border-border bg-surface/50 flex-shrink-0">
            <button
              type="button"
              onClick={handleChangeCustomer}
              disabled={isStreaming}
              className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-text transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className="h-3 w-3" />
              更换客户
            </button>
            {isStreaming && <span className="text-xs text-accent animate-pulse">Agent 正在执行...</span>}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center px-4">
                <span className="flex items-center justify-center h-12 w-12 rounded-full bg-accent/10 mb-4">
                  <Sparkles className="h-5 w-5 text-accent" />
                </span>
                <p className="text-sm font-medium text-text">助手已就绪</p>
                <p className="text-xs text-muted mt-1.5 leading-relaxed">
                  描述销售场景或诉求（如“王先生想了解医疗险保障范围”），
                  我会结合客户画像检索产品知识、生成话术并做合规检查。
                </p>
              </div>
            )}

            {messages.map((msg) =>
              msg.role === 'user' ? (
                <div key={msg.id} className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl px-3.5 py-2.5 bg-accent text-white rounded-br-md">
                    <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">{msg.content}</div>
                  </div>
                </div>
              ) : (
                <div key={msg.id} className="flex justify-start">
                  <div className="max-w-[92%] rounded-2xl px-3.5 py-2.5 bg-bg border border-border text-text rounded-bl-md">
                    <ToolStatusLog log={msg.toolLog} />

                    {msg.ragStatus === 'REFUSE' && (
                      <div className="mt-2 rounded-lg bg-warning/10 border border-warning/30 px-3 py-2">
                        <p className="text-xs text-warning font-medium">
                          ⚠️ 当前知识库没有足够的产品依据
                        </p>
                        <p className="text-xs text-muted mt-0.5">
                          Agent 未生成具体产品话术，以避免编造产品条款。
                        </p>
                      </div>
                    )}

                    <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {msg.content}
                      {msg.status === 'streaming' && (
                        <span className="inline-block w-1.5 h-4 bg-accent/60 ml-0.5 animate-pulse rounded-sm" />
                      )}
                    </div>

                    <CitationPanel citations={msg.citations} />
                    <CompliancePanel compliance={msg.compliance} />

                    {msg.status === 'error' && (
                      <div className="mt-3 rounded-lg bg-error/10 border border-error/30 px-3 py-2">
                        <p className="text-xs text-error font-medium">
                          {msg.errorMessage || '服务异常，请稍后重试。'}
                        </p>
                        <Button
                          variant="secondary"
                          size="sm"
                          className="mt-2"
                          onClick={() => retry(msg)}
                          disabled={isStreaming}
                        >
                          重试
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              )
            )}
            <div ref={chatEndRef} />
          </div>

          {/* 输入区 */}
          <div className="border-t border-border p-3.5 flex-shrink-0">
            <form onSubmit={handleSubmit} className="flex items-end gap-2">
              <Input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入问题或销售场景..."
                disabled={isStreaming}
                maxLength={2000}
                className="h-10 rounded-xl px-3.5"
              />
              {isStreaming ? (
                <Button variant="danger" size="md" type="button" onClick={() => abortRef.current?.abort()}>
                  中止
                </Button>
              ) : (
                <Button type="submit" disabled={!canSend} size="md">
                  发送
                </Button>
              )}
            </form>
          </div>
        </>
      )}
    </div>
  );
}
