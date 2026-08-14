import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { streamProductQa, type ChatMessage } from '../../services/productQaService';

const SUGGESTED_QUESTIONS = [
  '百万医疗险和重疾险有什么区别？',
  '安诊保慢病版，高血压患者能买吗？',
  '推荐一个适合30岁家庭的保险方案',
  '意外险的理赔流程是怎样的？',
];

export function ProductQaPage() {
  const user = useAuthStore((s) => s.user);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [sources, setSources] = useState<ChatMessage['sources']>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(question?: string) {
    const q = question || input.trim();
    if (!q || isStreaming) return;

    setInput('');
    setIsStreaming(true);

    // Add user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: q,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Add placeholder assistant message
    const assistantId = `assistant-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: 'assistant', content: '', timestamp: new Date(), isLoading: true },
    ]);
    setSources([]);

    try {
      for await (const event of streamProductQa(q)) {
        const { event: eventType, data } = event;

        if (eventType === 'token' && typeof data.content === 'string') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + data.content, isLoading: false }
                : m
            )
          );
        }

        if (eventType === 'reference_sources' && Array.isArray(data.sources)) {
          setSources(data.sources as ChatMessage['sources']);
        }

        if (eventType === 'error') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content || '抱歉，服务暂时不可用，请稍后重试。', isLoading: false }
                : m
            )
          );
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: '网络异常，请检查连接后重试。', isLoading: false }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    handleSend();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-text">AI 产品专家</h1>
            <Badge variant="warning">演示模式</Badge>
          </div>
          <p className="text-sm text-muted mt-0.5">
            基于知识库的智能保险产品问答，所有回答附带来源引用 [Demo]
          </p>
        </div>
        <button
          type="button"
          onClick={() => { setMessages([]); setSources([]); }}
          className="text-sm text-muted hover:text-accent transition-colors cursor-pointer"
        >
          清空对话
        </button>
      </div>

      {/* Chat Area */}
      <Card padding="none" className="flex-1 flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <span className="text-5xl mb-4">🤖</span>
              <h2 className="text-lg font-semibold text-text mb-2">
                你好，{user?.name || '代理人'}！我是安诊保 AI 产品专家
              </h2>
              <p className="text-sm text-muted max-w-md mb-6">
                我可以帮你查询保险产品信息、对比产品差异、推荐保险方案。
                请选择以下问题，或直接输入你的问题。
              </p>
              <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => handleSend(q)}
                    disabled={isStreaming}
                    className="text-sm bg-bg border border-border rounded-full px-3.5 py-2 hover:border-accent/40 hover:text-accent transition-colors cursor-pointer disabled:opacity-50 text-left"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-accent text-white rounded-br-md'
                    : 'bg-bg border border-border text-text rounded-bl-md'
                }`}
              >
                <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {msg.content}
                  {msg.isLoading && (
                    <span className="inline-block w-1.5 h-4 bg-accent/60 ml-0.5 animate-pulse rounded-sm" />
                  )}
                </div>
                <div className="flex items-center gap-1.5 mt-1.5">
                  <span className="text-[11px] opacity-60">
                    {msg.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  {msg.role === 'assistant' && (
                    <span className="text-[11px] opacity-40">AI</span>
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="border-t border-border px-4 py-3 bg-bg/50">
            <p className="text-xs font-medium text-muted mb-2">📖 参考来源</p>
            <div className="flex flex-wrap gap-2">
              {sources.map((s, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 text-xs bg-card border border-border rounded-lg px-2.5 py-1.5"
                >
                  <span className="text-accent">📄</span>
                  <span className="text-text">{s.title}</span>
                  <span className="text-muted">({Math.round(s.relevance_score * 100)}%)</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-border p-4 flex-shrink-0">
          <form onSubmit={handleSubmit} className="flex items-end gap-3">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入你的保险问题..."
                disabled={isStreaming}
                maxLength={2000}
                className="w-full h-11 rounded-xl border border-border bg-white px-4 pr-12 text-sm text-text placeholder:text-muted/50 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-50"
              />
              <span className="absolute right-3 bottom-3 text-[11px] text-muted/40">
                {input.length}/2000
              </span>
            </div>
            <Button type="submit" loading={isStreaming} disabled={!input.trim()} size="lg">
              发送
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
