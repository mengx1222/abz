import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import {
  CompliancePanel,
  CitationPanel,
  ToolStatusLog,
  type AgentMessage,
} from '../../components/assistant/chatParts';
import { getCustomer } from '../../services/customerService';
import {
  AgentHttpError,
  streamSalesAgentChat,
  type AgentCompleteData,
  type AgentEvent,
  type CitationItem,
  type ComplianceResult,
} from '../../services/salesAgentService';

// ---- 类型 ----

interface CustomerMinimal {
  id: string;
  name: string;
  age?: number | null;
  gender?: string | null;
  customer_type?: string | null;
  current_stage?: string | null;
  intention_level?: number | null;
  insurance_type?: string | null;
}

interface PageError {
  kind: 'permission' | 'network' | 'server';
  message: string;
}

const STAGE_LABELS: Record<string, string> = {
  initial_contact: '首次接触',
  needs_analysis: '需求挖掘',
  proposal: '方案呈现',
  negotiation: '异议处理',
  closing: '促成签约',
  follow_up: '售后跟进',
};

// ---- 合规/引用/工具状态面板已抽取至 components/assistant/chatParts（与全局助手共用） ----

// ---- 主页面 ----

export function SalesAgentPage() {
  // 路由 param 名为 customerId（/sales-agent/:customerId?）
  const { customerId: routeCustomerId } = useParams<{ customerId?: string }>();
  const navigate = useNavigate();

  const [customerId] = useState<string | null>(routeCustomerId || null);
  const [customer, setCustomer] = useState<CustomerMinimal | null>(null);
  const [customerLoading, setCustomerLoading] = useState<boolean>(!!routeCustomerId);
  const [pageError, setPageError] = useState<PageError | null>(null);

  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ---- 加载客户上下文（最小字段） ----
  useEffect(() => {
    if (!customerId) return;
    let cancelled = false;
    setCustomerLoading(true);
    setPageError(null);
    (async () => {
      try {
        const detail = await getCustomer(customerId);
        if (cancelled) return;
        if (!detail) {
          setPageError({ kind: 'permission', message: '客户不存在或无权访问。' });
          setCustomer(null);
          return;
        }
        setCustomer({
          id: customerId,
          name: detail.name || '未知客户',
          age: detail.age ?? null,
          gender: detail.gender ?? null,
          customer_type: detail.customer_type ?? null,
          current_stage: detail.current_stage ?? null,
          intention_level: detail.intention_level ?? null,
          insurance_type: detail.insurance_type ?? null,
        });
      } catch (err) {
        if (!cancelled) {
          const status = (err as { response?: { status?: number } }).response?.status;
          setPageError(
            status === 404 || status === 403
              ? { kind: 'permission', message: '客户不存在或无权访问。' }
              : { kind: 'network', message: '客户信息加载失败，请重试。' }
          );
        }
      } finally {
        if (!cancelled) setCustomerLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [customerId]);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages]);

  // 卸载时中止流
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const appendAssistant = useCallback((): string => {
    const id = `assistant-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setMessages((prev) => [
      ...prev,
      {
        id,
        role: 'assistant',
        content: '',
        toolLog: [],
        citations: [],
        compliance: null,
        ragStatus: null,
        status: 'streaming',
      },
    ]);
    return id;
  }, []);

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
          // updater 内追加，避免 messagesRef 滞后导致工具状态互相覆盖
          setMessages((prev) =>
            prev.map((m) => (m.id === id ? { ...m, toolLog: [...m.toolLog, action] } : m))
          );
        }
        break;
      }
      case 'rag_context': {
        const ragStatus = typeof data.status === 'string' ? data.status : null;
        const citations = Array.isArray(data.citations)
          ? (data.citations as CitationItem[])
          : [];
        patchAssistant(id, { ragStatus, citations });
        break;
      }
      case 'message_delta': {
        if (typeof data.content === 'string' && data.content) {
          // updater 内追加，避免 messagesRef 滞后导致流式内容互相覆盖
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
        // updater 内合并：agent_complete 未携带的字段保留 tool 阶段已收到的结果
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
                    typeof complete.rag_status === 'string'
                      ? complete.rag_status
                      : m.ragStatus,
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
    if (!q || isStreaming || !customerId) return;

    setInput('');
    setIsStreaming(true);
    setPageError(null);

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
    const assistantId = appendAssistant();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const event of streamSalesAgentChat(customerId, q, {
        productType: customer?.insurance_type ?? undefined,
        sessionId: sessionId ?? undefined,
        signal: controller.signal,
      })) {
        handleEvent(assistantId, event);
      }
      // 流正常结束兜底（updater 内判断，避免 messagesRef 滞后误覆盖已完成状态）
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
      if (err instanceof AgentHttpError) {
        if (err.status === 401) {
          patchAssistant(assistantId, {
            status: 'error',
            errorMessage: '登录已过期，请重新登录。',
          });
        } else if (err.status === 403 || err.status === 404) {
          patchAssistant(assistantId, {
            status: 'error',
            errorMessage: err.detailMessage || '客户不存在或无权访问。',
          });
        } else if (err.status === 0) {
          // 用户主动中止（updater 内判断已有内容，避免 messagesRef 滞后）
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
        } else {
          patchAssistant(assistantId, {
            status: 'error',
            errorMessage: err.detailMessage || `服务异常（HTTP ${err.status}）`,
          });
        }
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

  function handleAbort() {
    abortRef.current?.abort();
  }

  function retry(message: AgentMessage) {
    const text = message.content || message.errorMessage || '';
    if (!text.trim()) return;
    // 重试 = 新发起一次相同问题的请求（新消息，不重复持久化）
    setInput(text);
    // 直接发送
    void handleSend(text);
  }

  const canSend = !!customerId && !isStreaming && input.trim().length > 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-text">AI 销售副驾</h1>
            {customer && <Badge variant="primary">{customer.name}</Badge>}
            {customer?.insurance_type && (
              <Badge variant="info">{customer.insurance_type}</Badge>
            )}
          </div>
          <p className="text-sm text-muted mt-0.5">
            基于客户画像与产品知识库的销售助手，生成建议、话术与合规检查
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate('/customers')}>
            返回客户
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setMessages([]);
              setSessionId(null);
            }}
          >
            清空对话
          </Button>
        </div>
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* 左侧：客户上下文 + 执行状态 */}
        <div className="w-64 flex-shrink-0 flex flex-col gap-4 min-h-0">
          <Card padding="md">
            <h3 className="text-sm font-semibold text-text mb-3">客户上下文</h3>
            {customerLoading ? (
              <div className="text-sm text-muted animate-pulse">加载中...</div>
            ) : !customerId ? (
              <div className="text-sm text-muted">
                请从「客户360」进入客户详情，或在路由中携带客户 ID 打开本页。
              </div>
            ) : pageError ? (
              <div className="text-sm text-error">{pageError.message}</div>
            ) : customer ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted">姓名</span>
                  <span className="text-text">{customer.name}</span>
                </div>
                {customer.age != null && (
                  <div className="flex justify-between">
                    <span className="text-muted">年龄</span>
                    <span className="text-text">{customer.age}</span>
                  </div>
                )}
                {customer.customer_type && (
                  <div className="flex justify-between">
                    <span className="text-muted">类型</span>
                    <span className="text-text">{customer.customer_type}</span>
                  </div>
                )}
                {customer.current_stage && (
                  <div className="flex justify-between">
                    <span className="text-muted">阶段</span>
                    <span className="text-text">
                      {STAGE_LABELS[customer.current_stage] || customer.current_stage}
                    </span>
                  </div>
                )}
                {customer.intention_level != null && (
                  <div className="flex justify-between">
                    <span className="text-muted">意向等级</span>
                    <span className="text-text">{customer.intention_level}/5</span>
                  </div>
                )}
                {customer.insurance_type && (
                  <div className="flex justify-between">
                    <span className="text-muted">关注产品</span>
                    <span className="text-text">{customer.insurance_type}</span>
                  </div>
                )}
              </div>
            ) : null}
          </Card>

          <Card padding="md" className="flex-1 min-h-0 overflow-y-auto">
            <h3 className="text-sm font-semibold text-text mb-3">执行状态</h3>
            <div className="text-xs text-muted space-y-2">
              {messages.length === 0 && <p>等待任务...</p>}
              {messages
                .filter((m) => m.role === 'assistant')
                .slice(-3)
                .map((m) => (
                  <div key={m.id} className="space-y-1">
                    {m.toolLog.length > 0 ? (
                      <ToolStatusLog log={m.toolLog} />
                    ) : (
                      <div className="flex items-center gap-1.5">
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-muted/50" />
                        <span>{m.status === 'streaming' ? '正在执行...' : '已完成'}</span>
                      </div>
                    )}
                  </div>
                ))}
              {isStreaming && (
                <div className="text-accent animate-pulse">Agent 正在执行...</div>
              )}
            </div>
          </Card>
        </div>

        {/* 右侧：对话区 */}
        <Card padding="none" className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <span className="text-5xl mb-4">🤝</span>
                <h2 className="text-lg font-semibold text-text mb-2">AI 销售副驾已就绪</h2>
                <p className="text-sm text-muted max-w-md mb-6">
                  描述你的销售场景或客户诉求（如“客户想了解医疗险的保障范围”），
                  我会查询客户信息、检索产品知识、生成话术并执行合规检查。
                </p>
              </div>
            )}

            {messages.map((msg) =>
              msg.role === 'user' ? (
                <div key={msg.id} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-accent text-white rounded-br-md">
                    <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {msg.content}
                    </div>
                  </div>
                </div>
              ) : (
                <div key={msg.id} className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-bg border border-border text-text rounded-bl-md">
                    <ToolStatusLog log={msg.toolLog} />

                    {msg.ragStatus === 'REFUSE' && (
                      <div className="mt-2 rounded-lg bg-warning/10 border border-warning/30 px-3 py-2">
                        <p className="text-xs text-warning font-medium">
                          ⚠️ 当前知识库没有足够的产品依据
                        </p>
                        <p className="text-xs text-muted mt-0.5">
                          Agent 未生成具体产品话术，以避免编造产品条款。请补充产品知识文档后重试，
                          或咨询华安保险产品部门。
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

          {/* Input */}
          <div className="border-t border-border p-4 flex-shrink-0">
            <form onSubmit={handleSubmit} className="flex items-end gap-3">
              <div className="flex-1 relative">
                <Input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    customerId ? '输入销售场景或客户诉求...' : '请先从客户360选择客户'
                  }
                  disabled={isStreaming || !customerId}
                  maxLength={2000}
                  className="h-11 rounded-xl px-4 pr-12 disabled:opacity-50"
                />
                <span className="absolute right-3 bottom-3 text-[11px] text-muted/40">
                  {input.length}/2000
                </span>
              </div>
              {isStreaming ? (
                <Button variant="danger" size="lg" type="button" onClick={handleAbort}>
                  中止
                </Button>
              ) : (
                <Button type="submit" loading={isStreaming} disabled={!canSend} size="lg">
                  发送
                </Button>
              )}
            </form>
            {pageError && pageError.kind === 'permission' && (
              <p className="mt-2 text-xs text-error">{pageError.message}</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
