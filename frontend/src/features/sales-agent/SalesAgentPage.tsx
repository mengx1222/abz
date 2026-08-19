import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { customerService } from '../../services/customerService';
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

interface AgentMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolLog: string[];
  citations: CitationItem[];
  compliance: ComplianceResult | null;
  ragStatus: string | null;
  status: 'streaming' | 'completed' | 'refused' | 'error';
  errorMessage?: string;
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

function formatScore(score?: number): string {
  if (score === undefined || score === null) return '';
  return `（${Math.round(score * 100)}%）`;
}

// ---- 合规面板（真实绑定后端结果） ----

const COMPLIANCE_META: Record<
  ComplianceResult['status'],
  { variant: 'success' | 'warning' | 'danger'; label: string; hint: string }
> = {
  GREEN: { variant: 'success', label: '合规通过', hint: '合规检查通过，内容可正常使用。' },
  YELLOW: { variant: 'warning', label: '建议人工确认', hint: '存在需要人工确认的表述，请修改或复核后再使用。' },
  RED: { variant: 'danger', label: '禁止直接对客使用', hint: '检测到违规表述，该内容不可直接用于客户沟通。' },
};

function CompliancePanel({ compliance }: { compliance: ComplianceResult | null }) {
  if (!compliance) return null;
  const meta = COMPLIANCE_META[compliance.status] || COMPLIANCE_META.GREEN;
  return (
    <div className="mt-3 rounded-xl border border-border bg-bg/60 p-3">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-xs font-medium text-muted">合规检查</span>
        <Badge variant={meta.variant}>{meta.label}</Badge>
      </div>
      <p className="text-xs text-muted">{meta.hint}</p>
      {compliance.issues && compliance.issues.length > 0 && (
        <ul className="mt-2 space-y-1">
          {compliance.issues.slice(0, 5).map((issue, i) => (
            <li key={i} className="text-xs text-muted flex gap-1.5">
              <span>·</span>
              <span>
                {issue.rule}
                {issue.suggestion ? `：${issue.suggestion}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---- 引用面板 ----

function CitationPanel({ citations }: { citations: CitationItem[] }) {
  if (!citations || citations.length === 0) return null;
  return (
    <div className="mt-3 rounded-xl border border-border bg-bg/60 p-3">
      <p className="text-xs font-medium text-muted mb-2">📖 产品知识来源</p>
      <div className="flex flex-wrap gap-2">
        {citations.map((c, i) => (
          <div
            key={i}
            className="flex items-center gap-1.5 text-xs bg-card border border-border rounded-lg px-2.5 py-1.5"
          >
            <span className="text-accent">📄</span>
            <span className="text-text">{c.document_title || '未知文档'}</span>
            {c.section ? <span className="text-muted">· {c.section}</span> : null}
            {formatScore(c.score) && <span className="text-muted">{formatScore(c.score)}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- 工具执行状态（仅安全状态说明，不暴露内部 prompt/reasoning） ----

function ToolStatusLog({ log }: { log: string[] }) {
  if (log.length === 0) return null;
  return (
    <div className="mt-2 space-y-0.5">
      {log.map((step, i) => (
        <div key={i} className="flex items-center gap-1.5 text-xs text-muted">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent/60" />
          <span>{step}</span>
        </div>
      ))}
    </div>
  );
}

// ---- 主页面 ----

export function SalesAgentPage() {
  const { id: routeCustomerId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [customerId, setCustomerId] = useState<string | null>(routeCustomerId || null);
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
        const detail = await customerService.getCustomer(customerId);
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
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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
          patchAssistant(id, { toolLog: [...(messagesRef.current.get(id)?.toolLog || []), action] });
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
          const cur = messagesRef.current.get(id);
          patchAssistant(id, { content: (cur?.content || '') + data.content });
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
        const citations = Array.isArray(complete.citations) ? complete.citations : [];
        const compliance = (complete.compliance as ComplianceResult | null) || null;
        const ragStatus = typeof complete.rag_status === 'string' ? complete.rag_status : null;
        patchAssistant(id, {
          status: complete.status === 'refused' ? 'refused' : 'completed',
          content: msg,
          citations,
          compliance,
          ragStatus,
        });
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

  // messagesRef 供事件回调内读取最新状态
  const messagesRef = useRef<Map<string, AgentMessage>>(new Map());
  useEffect(() => {
    messagesRef.current = new Map(messages.map((m) => [m.id, m]));
  }, [messages]);

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
      // 流正常结束（未收到 agent_complete/error 的兜底）
      const cur = messagesRef.current.get(assistantId);
      if (cur && cur.status === 'streaming') {
        patchAssistant(assistantId, {
          status: cur.content ? 'completed' : 'error',
          errorMessage: cur.content ? undefined : 'Agent 未返回结果，请重试。',
        });
      }
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
          // 用户主动中止
          const cur = messagesRef.current.get(assistantId);
          patchAssistant(assistantId, {
            status: cur?.content ? 'completed' : 'error',
            errorMessage: cur?.content ? undefined : '已中止。',
          });
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
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    customerId ? '输入销售场景或客户诉求...' : '请先从客户360选择客户'
                  }
                  disabled={isStreaming || !customerId}
                  maxLength={2000}
                  className="w-full h-11 rounded-xl border border-border bg-white px-4 pr-12 text-sm text-text placeholder:text-muted/50 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-50"
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
