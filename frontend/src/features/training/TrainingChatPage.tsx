import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { Card } from '../../components/ui/Card';
import {
  startSession,
  streamTrainingMessage,
  streamTrainingScore,
  type TrainingSession,
  type TrainingMessage,
  type TrainingScore,
  type SSEEvent,
} from '../../services/trainingService';

// ---- Constants ----

};

const ROLE_CONFIG: Record<string, { label: string; align: string; bg: string; avatar: string; avatarBg: string }> = {
  agent: { label: '我', align: 'justify-end', bg: 'bg-accent text-white', avatar: '我', avatarBg: 'bg-accent' },
  customer: { label: '客户', align: 'justify-start', bg: 'bg-card border border-border', avatar: '客', avatarBg: 'bg-rose-100 text-rose-600' },
  coach: { label: '教练', align: 'justify-start', bg: 'bg-emerald-50 border border-emerald-200', avatar: '💡', avatarBg: 'bg-emerald-100' },
};

export function TrainingChatPage() {
  const navigate = useNavigate();
  const { scenarioId } = useParams<{ scenarioId: string }>();

  // State
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [messages, setMessages] = useState<TrainingMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isScoring, setIsScoring] = useState(false);
  const [scoringText, setScoringText] = useState('');
  const [score, setScore] = useState<TrainingScore | null>(null);
  const [coachingHint, setCoachingHint] = useState<{ hint: string; category: string } | null>(null);
  const [customerStreaming, setCustomerStreaming] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Load session
  useEffect(() => {
    if (!scenarioId) return;
    let mounted = true;

    (async () => {
      try {
        const sess = await startSession(scenarioId);
        if (mounted) {
          setSession(sess);
          setLoading(false);
          setTimeout(() => inputRef.current?.focus(), 100);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    })();

    return () => { mounted = false; };
  }, [scenarioId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, coachingHint, scoringText]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || !session || isSending) return;

    const content = input.trim();
    setInput('');
    setIsSending(true);
    setCoachingHint(null);

    // Add agent message optimistically
    const agentMsg: TrainingMessage = {
      id: `temp-agent-${Date.now()}`,
      role: 'agent',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, agentMsg]);

    // Add streaming customer message placeholder
    setCustomerStreaming(true);
    const customerMsgId = `temp-customer-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: customerMsgId, role: 'customer', content: '', created_at: new Date().toISOString() },
    ]);

    try {
      for await (const event of streamTrainingMessage(session.id, content)) {
        const { event: eventType, data } = event as SSEEvent;

        switch (eventType) {
          case 'message_start':
            break;

          case 'token': {
            const tokenContent = data.content as string;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === customerMsgId
                  ? { ...m, content: m.content + tokenContent }
                  : m,
              ),
            );
            break;
          }

          case 'coaching': {
            setCoachingHint({
              hint: data.hint as string,
              category: data.category as string,
            });
            break;
          }

          case 'turn_complete': {
            setCustomerStreaming(false);
            break;
          }

          case 'error': {
            setCustomerStreaming(false);
            break;
          }
        }
      }
    } catch (err) {
      setCustomerStreaming(false);
      console.error('Training message error:', err);
    } finally {
      setIsSending(false);
    }
  }, [input, session, isSending]);

  const handleComplete = useCallback(async () => {
    if (!session || isScoring) return;

    setIsScoring(true);
    setScoringText('');

    try {
      for await (const event of streamTrainingScore(session.id)) {
        const { event: eventType, data } = event as SSEEvent;

        switch (eventType) {
          case 'scoring_start':
            break;

          case 'token': {
            setScoringText((prev) => prev + (data.content as string));
            break;
          }

          case 'score_data': {
            setScore({
              total_score: data.total_score as number,
              product_accuracy: data.product_accuracy as number,
              empathy: data.empathy as number,
              closing_action: data.closing_action as number,
              strengths: data.strengths as string[],
              weaknesses: data.weaknesses as string[],
              recommendations: data.recommendations as string[],
            });
            break;
          }

          case 'scoring_complete': {
            setIsScoring(false);
            break;
          }
        }
      }
    } catch (err) {
      setIsScoring(false);
      console.error('Scoring error:', err);
    }
  }, [session, isScoring]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner size="lg" />
        <span className="ml-3 text-muted">正在初始化训练场景...</span>
      </div>
    );
  }

  const scenario = session?.scenario_title || '';
  const persona = (session as unknown as Record<string, unknown>)?.customer_persona as Record<string, string> | undefined;

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/training')}
            className="p-1 rounded hover:bg-bg text-muted hover:text-text transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="text-lg font-semibold text-text">{scenario}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <Badge variant="default">训练中</Badge>
              <span className="text-xs text-muted">
                对话 {messages.filter((m) => m.role === 'agent').length} 轮
              </span>
            </div>
          </div>
        </div>
        <Button
          variant="primary"
          size="sm"
          disabled={isScoring || messages.filter((m) => m.role === 'agent').length < 2}
          onClick={handleComplete}
        >
          {isScoring ? (
            <span className="flex items-center gap-2">
              <LoadingSpinner size="sm" />
              评分中...
            </span>
          ) : (
            '结束训练 · 查看评分'
          )}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Chat Area */}
        <div className="lg:col-span-3">
          <Card padding="md" className="min-h-[500px] flex flex-col">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-3 mb-4 max-h-[60vh] pr-1">
              {messages.length === 0 && (
                <div className="text-center py-12">
                  <div className="text-3xl mb-3 opacity-20">🎯</div>
                  <p className="text-muted text-sm">
                    {persona ? `您正在与${persona.name || '客户'}对话` : '开始您的销售话术练习'}
                  </p>
                  {persona?.key_objections && (
                    <div className="mt-2 flex flex-wrap gap-1 justify-center">
                      {Array.isArray(persona.key_objections) && persona.key_objections.map((obj: string) => (
                        <span key={obj} className="px-2 py-0.5 rounded text-xs bg-rose-50 text-rose-500">
                          {obj}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {messages.map((msg) => {
                const cfg = ROLE_CONFIG[msg.role] || ROLE_CONFIG.agent;
                return (
                  <div key={msg.id} className={`flex ${cfg.align} gap-2`}>
                    {cfg.align === 'justify-start' && (
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${cfg.avatarBg}`}>
                        {cfg.avatar}
                      </div>
                    )}
                    <div className={`max-w-[75%] px-3 py-2 rounded-xl text-sm ${cfg.bg}`}>
                      <span className="whitespace-pre-wrap">{msg.content}</span>
                      {msg.role === 'customer' && msg.content === '' && customerStreaming && (
                        <span className="inline-block w-1.5 h-4 bg-rose-400 ml-0.5 animate-pulse rounded-sm" />
                      )}
                    </div>
                    {cfg.align === 'justify-end' && (
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${cfg.avatarBg}`}>
                        {cfg.avatar}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Scoring Text */}
              {scoringText && (
                <div className="flex justify-start gap-2">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 bg-amber-100 text-amber-600">
                    📊
                  </div>
                  <div className="max-w-[75%] px-3 py-2 rounded-xl text-sm bg-amber-50 border border-amber-200">
                    <span className="whitespace-pre-wrap">{scoringText}</span>
                    {isScoring && (
                      <span className="inline-block w-1.5 h-4 bg-amber-400 ml-0.5 animate-pulse rounded-sm" />
                    )}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            {!isScoring && (
              <div className="flex gap-2 pt-2 border-t border-border">
                <Input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入您的销售话术..."
                  disabled={isSending}
                  className="flex-1"
                />
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!input.trim() || isSending}
                  onClick={handleSend}
                >
                  {isSending ? <LoadingSpinner size="sm" /> : '发送'}
                </Button>
              </div>
            )}
          </Card>
        </div>

        {/* Sidebar: Coaching + Info */}
        <div className="lg:col-span-1 space-y-3">
          {/* Customer Info Card */}
          {persona && (
            <Card padding="md">
              <h3 className="text-sm font-semibold text-text mb-2">客户人设</h3>
              <div className="space-y-1.5 text-xs text-muted">
                {persona.name && <p>👤 {persona.name}，{persona.age || '?'}岁</p>}
                {persona.personality && <p>🧠 {persona.personality}</p>}
                {persona.mood && <p>😊 {persona.mood}</p>}
                {persona.insurance_knowledge && <p>📚 保险认知：{persona.insurance_knowledge}</p>}
                {Array.isArray(persona.key_objections) && persona.key_objections.length > 0 && (
                  <div className="mt-1">
                    <p className="font-medium text-text">关键异议：</p>
                    {persona.key_objections.map((obj: string) => (
                      <span key={obj} className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-rose-50 text-rose-500 mr-1 mt-1">
                        {obj}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Coaching Hint */}
          {coachingHint && (
            <Card padding="md" className="border-emerald-200 bg-emerald-50/30">
              <h3 className="text-sm font-semibold text-emerald-700 mb-2">💡 教练提示</h3>
              <p className="text-xs text-text/80 leading-relaxed">{coachingHint.hint}</p>
              <div className="mt-2">
                <Badge variant="success" className="text-[10px]">
                  {coachingHint.category === 'empathy' ? '共情' : coachingHint.category === 'product' ? '产品' : '促单'}
                </Badge>
              </div>
            </Card>
          )}

          {/* Score Panel */}
          {score && (
            <Card padding="md" className="border-accent/30 bg-accent/5">
              <h3 className="text-sm font-semibold text-text mb-3">训练评分</h3>
              <div className="text-center mb-3">
                <div className={`text-3xl font-bold ${
                  score.total_score >= 85 ? 'text-emerald-500' :
                  score.total_score >= 70 ? 'text-amber-500' : 'text-red-500'
                }`}>
                  {score.total_score}
                </div>
                <p className="text-xs text-muted">综合评分</p>
              </div>

              {/* Score Bars */}
              <div className="space-y-2">
                {[
                  { label: '产品准确性', value: score.product_accuracy },
                  { label: '客户共情', value: score.empathy },
                  { label: '促单动作', value: score.closing_action },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-muted">{item.label}</span>
                      <span className="text-text font-medium">{item.value}</span>
                    </div>
                    <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          item.value >= 85 ? 'bg-emerald-500' :
                          item.value >= 70 ? 'bg-amber-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Strengths */}
              {score.strengths.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium text-emerald-600 mb-1">✅ 优势</p>
                  {score.strengths.map((s, i) => (
                    <p key={i} className="text-xs text-muted">· {s}</p>
                  ))}
                </div>
              )}

              {/* Weaknesses */}
              {score.weaknesses.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-amber-600 mb-1">⚠️ 待提升</p>
                  {score.weaknesses.map((w, i) => (
                    <p key={i} className="text-xs text-muted">· {w}</p>
                  ))}
                </div>
              )}

              {/* Recommendations */}
              {score.recommendations.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-accent mb-1">📌 建议</p>
                  {score.recommendations.map((r, i) => (
                    <p key={i} className="text-xs text-muted">· {r}</p>
                  ))}
                </div>
              )}

              <button
                onClick={() => navigate('/training')}
                className="mt-3 w-full text-center text-xs text-accent hover:underline cursor-pointer"
              >
                返回训练列表
              </button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
