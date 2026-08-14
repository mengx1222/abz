import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import {
  streamScriptGenerate,
  getScripts,
  getScript,
  toggleFavorite,
  deleteScript,
  checkCompliance,
  type CustomerContext,
  type Script,
  type ComplianceResult,
  type ComplianceIssue,
} from '../../services/scriptService';

// ---- 常量 ----

const STYLE_MAP: Record<string, { label: string; color: string; bg: string }> = {
  affinity: { label: '亲和型', color: 'text-rose-600', bg: 'bg-rose-50' },
  professional: { label: '专业型', color: 'text-blue-600', bg: 'bg-blue-50' },
  data_driven: { label: '数据驱动型', color: 'text-emerald-600', bg: 'bg-emerald-50' },
  concise: { label: '简洁型', color: 'text-violet-600', bg: 'bg-violet-50' },
};

const PRODUCT_TYPES = ['全部', '医疗险', '重疾险', '意外险', '年金险', '寿险', '车险'];

const STAGE_OPTIONS = [
  { value: '', label: '选择销售阶段' },
  { value: 'initial_contact', label: '首次接触' },
  { value: 'needs_analysis', label: '需求挖掘' },
  { value: 'proposal', label: '方案呈现' },
  { value: 'negotiation', label: '异议处理' },
  { value: 'closing', label: '促成签约' },
  { value: 'follow_up', label: '售后跟进' },
];

const OBJECTION_OPTIONS = [
  { value: '', label: '选择客户异议' },
  { value: '太贵了', label: '太贵了' },
  { value: '我有社保了', label: '我有社保了' },
  { value: '没必要买', label: '没必要买' },
  { value: '考虑一下', label: '考虑一下' },
  { value: '网上更便宜', label: '网上更便宜' },
  { value: '身体好不需要', label: '身体好不需要' },
  { value: '以前买过保险', label: '以前买过保险' },
];

const COMPLIANCE_CONFIG: Record<string, { label: string; variant: 'success' | 'warning' | 'error' }> = {
  green: { label: '合规通过', variant: 'success' },
  yellow: { label: '建议修改', variant: 'warning' },
  red: { label: '禁止使用', variant: 'error' },
};

// ---- Sub-components ----

function ComplianceBadge({ status }: { status: string }) {
  const config = COMPLIANCE_CONFIG[status] || COMPLIANCE_CONFIG.green;
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

function CompliancePanel({ result }: { result: ComplianceResult | null }) {
  if (!result) return null;
  return (
    <div className={`p-3 rounded-lg border ${
      result.status === 'red' ? 'border-red-200 bg-red-50/50' :
      result.status === 'yellow' ? 'border-yellow-200 bg-yellow-50/50' :
      'border-green-200 bg-green-50/50'
    }`}>
      <div className="flex items-center gap-2 mb-2">
        <ComplianceBadge status={result.status} />
        <span className="text-xs text-muted">合规评分：{result.score}/100</span>
      </div>
      {result.issues.length > 0 && (
        <div className="space-y-2">
          {result.issues.map((issue: ComplianceIssue, idx: number) => (
            <div key={idx} className="text-xs space-y-0.5">
              <div className="flex items-center gap-1">
                <Badge variant={issue.severity === 'RED' ? 'error' : 'warning'} className="text-[10px] px-1.5 py-0">
                  {issue.rule}
                </Badge>
              </div>
              <p className="text-text/80 pl-1">「{issue.matched_text}」</p>
              <p className="text-emerald-600 pl-1">建议：{issue.suggestion}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StyleScriptCard({
  style,
  content,
  compliance,
  wordCount,
  isStreaming,
}: {
  style: string;
  content: string;
  compliance: ComplianceResult | null;
  wordCount?: number;
  isStreaming: boolean;
}) {
  const meta = STYLE_MAP[style] || STYLE_MAP.professional;
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [content]);

  return (
    <Card padding="md" className="relative">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${meta.bg} ${meta.color}`}>
            {meta.label}
          </span>
          {wordCount && !isStreaming && (
            <span className="text-xs text-muted">{wordCount}字</span>
          )}
          {isStreaming && (
            <span className="text-xs text-accent animate-pulse">生成中...</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {compliance && <ComplianceBadge status={compliance.status} />}
          <button
            onClick={handleCopy}
            className="p-1 rounded hover:bg-bg text-muted hover:text-text transition-colors"
            title="复制话术"
          >
            {copied ? (
              <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            )}
          </button>
        </div>
      </div>
      <div className={`text-sm leading-relaxed text-text/90 whitespace-pre-wrap ${isStreaming ? '' : ''}`}>
        {content}
        {isStreaming && <span className="inline-block w-1.5 h-4 bg-accent ml-0.5 animate-pulse rounded-sm" />}
      </div>
      {!isStreaming && compliance && compliance.issues.length > 0 && (
        <div className="mt-3">
          <CompliancePanel result={compliance} />
        </div>
      )}
    </Card>
  );
}

// ---- Main Page ----

type TabView = 'generate' | 'library';

export function ScriptsPage() {
  const user = useAuthStore((s) => s.user);
  const [activeTab, setActiveTab] = useState<TabView>('generate');
  const [activeProduct, setActiveProduct] = useState('全部');

  // ---- Generate State ----
  const [isGenerating, setIsGenerating] = useState(false);
  const [genForm, setGenForm] = useState({
    name: '',
    age: '',
    customer_type: '',
    stage: '',
    objection: '',
    product_type: '',
  });
  const [genStyle, setGenStyle] = useState<string>('');
  const [genResults, setGenResults] = useState<Record<string, { content: string; compliance: ComplianceResult | null; wordCount: number; streaming: boolean }>>({});
  const [genRequestId, setGenRequestId] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  // ---- Library State ----
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loadingScripts, setLoadingScripts] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedScript, setSelectedScript] = useState<Script | null>(null);
  const [scriptDetail, setScriptDetail] = useState<Script | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Load scripts on tab switch
  useEffect(() => {
    if (activeTab === 'library') {
      loadScripts();
    }
  }, [activeTab, activeProduct]);

  // Load script detail
  useEffect(() => {
    if (selectedScript) {
      setLoadingDetail(true);
      getScript(selectedScript.id)
        .then(setScriptDetail)
        .catch(() => setScriptDetail(null))
        .finally(() => setLoadingDetail(false));
    }
  }, [selectedScript]);

  const loadScripts = useCallback(async () => {
    setLoadingScripts(true);
    try {
      const filters: Record<string, string | null> = { search: searchQuery || null };
      if (activeProduct !== '全部') filters.product_type = activeProduct;
      const data = await getScripts(filters);
      setScripts(data);
    } catch {
      setScripts([]);
    } finally {
      setLoadingScripts(false);
    }
  }, [activeProduct, searchQuery]);

  const handleGenerate = async () => {
    if (!genForm.name.trim()) return;

    setIsGenerating(true);
    setGenResults({});
    abortRef.current = new AbortController();

    const params: CustomerContext = {
      name: genForm.name,
      age: genForm.age ? parseInt(genForm.age) : null,
      customer_type: genForm.customer_type || null,
      stage: genForm.stage || null,
      objection: genForm.objection || null,
      product_type: genForm.product_type || null,
    };

    try {
      for await (const event of streamScriptGenerate({
        customer_context: params,
        style: genStyle || null,
        product_type: genForm.product_type || null,
      })) {
        const { event: eventType, data } = event;

        switch (eventType) {
          case 'generation_start':
            setGenRequestId(String(data.request_id));
            (data.styles as string[]).forEach((s) => {
              setGenResults((prev) => ({
                ...prev,
                [s]: { content: '', compliance: null, wordCount: 0, streaming: true },
              }));
            });
            break;

          case 'rag_context':
            // RAG知识检索完成
            break;

          case 'style_start':
            setGenResults((prev) => ({
              ...prev,
              [data.style as string]: { content: '', compliance: null, wordCount: 0, streaming: true },
            }));
            break;

          case 'token': {
            const style = data.style as string;
            const token = data.content as string;
            setGenResults((prev) => {
              const existing = prev[style] || { content: '', compliance: null, wordCount: 0, streaming: true };
              return {
                ...prev,
                [style]: { ...existing, content: existing.content + token },
              };
            });
            break;
          }

          case 'style_complete': {
            const style = data.style as string;
            const content = data.content as string;
            const compliance = data.compliance as ComplianceResult;
            const wordCount = (data.word_count as number) || content.length;
            setGenResults((prev) => ({
              ...prev,
              [style]: { content, compliance, wordCount, streaming: false },
            }));
            break;
          }

          case 'generation_complete':
            setIsGenerating(false);
            break;
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        console.error('Script generation error:', err);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleStopGeneration = () => {
    abortRef.current?.abort();
    setIsGenerating(false);
    // Mark all streaming styles as done
    setGenResults((prev) => {
      const updated = { ...prev };
      for (const key of Object.keys(updated)) {
        updated[key] = { ...updated[key], streaming: false };
      }
      return updated;
    });
  };

  const handleFavorite = async (scriptId: string) => {
    try {
      const updated = await toggleFavorite(scriptId);
      setScripts((prev) =>
        prev.map((s) => (s.id === scriptId ? { ...s, favorited_count: updated.favorited_count } : s))
      );
    } catch { /* ignore */ }
  };

  const handleDeleteScript = async (scriptId: string) => {
    try {
      await deleteScript(scriptId);
      setScripts((prev) => prev.filter((s) => s.id !== scriptId));
      if (selectedScript?.id === scriptId) setSelectedScript(null);
    } catch { /* ignore */ }
  };

  const handleBackToList = () => {
    setSelectedScript(null);
    setScriptDetail(null);
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">AI话术</h1>
          </div>
          <p className="text-muted text-sm mt-1">
            {user?.name || '用户'}，AI生成个性化销售话术，多风格对比，合规自动检查
          </p>
        </div>
        <div className="flex gap-1 bg-card rounded-lg p-0.5 border border-border">
          <button
            onClick={() => setActiveTab('generate')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer ${
              activeTab === 'generate'
                ? 'bg-accent text-white shadow-sm'
                : 'text-muted hover:text-text'
            }`}
          >
            生成话术
          </button>
          <button
            onClick={() => setActiveTab('library')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer ${
              activeTab === 'library'
                ? 'bg-accent text-white shadow-sm'
                : 'text-muted hover:text-text'
            }`}
          >
            话术库
          </button>
        </div>
      </div>

      {/* ---- Tab: Generate ---- */}
      {activeTab === 'generate' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: Form */}
          <div className="lg:col-span-1 space-y-3">
            <Card padding="md">
              <h2 className="text-base font-semibold text-text mb-3">客户信息</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-muted block mb-1">客户姓名 *</label>
                  <Input
                    value={genForm.name}
                    onChange={(e) => setGenForm({ ...genForm, name: e.target.value })}
                    placeholder="输入客户姓名"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">年龄</label>
                  <Input
                    value={genForm.age}
                    onChange={(e) => setGenForm({ ...genForm, age: e.target.value })}
                    placeholder="例如：45"
                    type="number"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">客户类型</label>
                  <Input
                    value={genForm.customer_type}
                    onChange={(e) => setGenForm({ ...genForm, customer_type: e.target.value })}
                    placeholder="例如：企业主、宝妈、白领"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">销售阶段</label>
                  <select
                    value={genForm.stage}
                    onChange={(e) => setGenForm({ ...genForm, stage: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-bg text-sm text-text focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    {STAGE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">客户异议</label>
                  <select
                    value={genForm.objection}
                    onChange={(e) => setGenForm({ ...genForm, objection: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-bg text-sm text-text focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    {OBJECTION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">产品类型</label>
                  <select
                    value={genForm.product_type}
                    onChange={(e) => setGenForm({ ...genForm, product_type: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-bg text-sm text-text focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    <option value="">选择产品</option>
                    {PRODUCT_TYPES.filter((p) => p !== '全部').map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
              </div>
            </Card>

            {/* Style Selection */}
            <Card padding="md">
              <h2 className="text-base font-semibold text-text mb-3">话术风格</h2>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setGenStyle('')}
                  className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                    genStyle === ''
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-muted hover:border-accent/50 hover:text-text'
                  }`}
                >
                  全部风格
                </button>
                {Object.entries(STYLE_MAP).map(([key, meta]) => (
                  <button
                    key={key}
                    onClick={() => setGenStyle(key === genStyle ? '' : key)}
                    className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                      genStyle === key
                        ? `border-current ${meta.bg} ${meta.color}`
                        : 'border-border text-muted hover:border-accent/50 hover:text-text'
                    }`}
                  >
                    {meta.label}
                  </button>
                ))}
              </div>
            </Card>

            {/* Generate Button */}
            <Button
              variant="primary"
              className="w-full"
              disabled={!genForm.name.trim() || isGenerating}
              onClick={isGenerating ? handleStopGeneration : handleGenerate}
            >
              {isGenerating ? (
                <span className="flex items-center justify-center gap-2">
                  <LoadingSpinner size="sm" />
                  停止生成
                </span>
              ) : (
                '生成话术'
              )}
            </Button>
            {genForm.name.trim() && !isGenerating && (
              <p className="text-xs text-muted text-center">
                将为{genStyle ? STYLE_MAP[genStyle]?.label : '全部4种风格'}生成话术
              </p>
            )}
          </div>

          {/* Right: Results */}
          <div className="lg:col-span-2 space-y-3">
            {Object.keys(genResults).length === 0 && !isGenerating && (
              <div className="text-center py-20">
                <div className="text-4xl mb-4 opacity-20">💬</div>
                <p className="text-muted text-sm">填写客户信息后，AI将为您生成个性化销售话术</p>
                <p className="text-muted/60 text-xs mt-1">支持亲和型、专业型、数据驱动型、简洁型四种风格</p>
              </div>
            )}

            {isGenerating && Object.keys(genResults).length === 0 && (
              <div className="flex flex-col items-center justify-center py-20">
                <LoadingSpinner size="lg" />
                <p className="text-sm text-muted mt-4">正在检索知识库，准备生成话术...</p>
              </div>
            )}

            {Object.entries(genResults).map(([style, result]) => (
              <StyleScriptCard
                key={style}
                style={style}
                content={result.content}
                compliance={result.compliance}
                wordCount={result.wordCount}
                isStreaming={result.streaming}
              />
            ))}

            {genRequestId && !isGenerating && Object.keys(genResults).length > 0 && (
              <div className="text-center py-2">
                <p className="text-xs text-muted">
                  ✅ 话术生成完成 · 话术已保存至话术库 · 
                  <button
                    onClick={() => setActiveTab('library')}
                    className="text-accent hover:underline cursor-pointer"
                  >
                    查看话术库
                  </button>
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- Tab: Library ---- */}
      {activeTab === 'library' && (
        <div className="space-y-3">
          {/* Toolbar */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索话术..."
                icon={
                  <svg className="w-4 h-4 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                }
              />
            </div>
            <div className="flex gap-1 flex-wrap">
              {PRODUCT_TYPES.map((pt) => (
                <button
                  key={pt}
                  onClick={() => setActiveProduct(pt)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                    activeProduct === pt
                      ? 'bg-accent text-white'
                      : 'bg-card border border-border text-muted hover:text-text'
                  }`}
                >
                  {pt}
                </button>
              ))}
            </div>
          </div>

          {/* Script List */}
          {loadingScripts ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : selectedScript ? (
            /* Detail View */
            <div className="space-y-3">
              <button
                onClick={handleBackToList}
                className="text-sm text-accent hover:underline cursor-pointer flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                返回列表
              </button>

              {loadingDetail ? (
                <div className="flex justify-center py-12">
                  <LoadingSpinner size="lg" />
                </div>
              ) : scriptDetail ? (
                <Card padding="md">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h2 className="text-lg font-semibold text-text">{scriptDetail.title}</h2>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          (STYLE_MAP[scriptDetail.style]?.bg || '') + ' ' + (STYLE_MAP[scriptDetail.style]?.color || '')
                        }`}>
                          {STYLE_MAP[scriptDetail.style]?.label || scriptDetail.style}
                        </span>
                        {scriptDetail.product_type && (
                          <Badge variant="default">{scriptDetail.product_type}</Badge>
                        )}
                        <ComplianceBadge status={scriptDetail.compliance_status} />
                        <Badge variant={scriptDetail.status === 'published' ? 'success' : 'default'}>
                          {scriptDetail.status === 'published' ? '已发布' : '草稿'}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleFavorite(scriptDetail.id)}
                        className="p-2 rounded-lg hover:bg-bg text-muted hover:text-rose-500 transition-colors"
                        title="收藏"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteScript(scriptDetail.id)}
                        className="p-2 rounded-lg hover:bg-red-50 text-muted hover:text-red-500 transition-colors"
                        title="删除"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Customer Context */}
                  {scriptDetail.customer_context && (
                    <div className="mb-3 p-2 rounded-lg bg-bg/50 text-xs space-y-0.5">
                      <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-muted">
                        {scriptDetail.customer_context.name && <span>客户：{scriptDetail.customer_context.name}</span>}
                        {scriptDetail.customer_context.age && <span>年龄：{scriptDetail.customer_context.age}岁</span>}
                        {scriptDetail.customer_context.stage && <span>阶段：{scriptDetail.customer_context.stage}</span>}
                        {scriptDetail.customer_context.objection && <span>异议：{scriptDetail.customer_context.objection}</span>}
                      </div>
                    </div>
                  )}

                  {/* Content */}
                  <div className="text-sm leading-relaxed text-text/90 whitespace-pre-wrap mb-3">
                    {scriptDetail.content}
                  </div>

                  {/* Compliance */}
                  {scriptDetail.compliance_issues && (
                    <CompliancePanel result={scriptDetail.compliance_issues} />
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-border text-xs text-muted">
                    <span>使用 {scriptDetail.usage_count} 次 · 收藏 {scriptDetail.favorited_count}</span>
                    <span>{scriptDetail.updated_at}</span>
                  </div>
                </Card>
              ) : (
                <p className="text-center text-muted py-8">加载失败</p>
              )}
            </div>
          ) : scripts.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4 opacity-20">📝</div>
              <p className="text-muted text-sm">暂无话术 · 去生成第一条吧</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {scripts.map((script) => (
                <Card
                  key={script.id}
                  padding="md"
                  hover
                  onClick={() => setSelectedScript(script)}
                  className="cursor-pointer"
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-sm">{script.title}</CardTitle>
                      <ComplianceBadge status={script.compliance_status} />
                    </div>
                    <CardDescription className="line-clamp-2">
                      {script.content
                        ? script.content.length > 100
                          ? script.content.slice(0, 100) + '...'
                          : script.content
                        : '暂无内容'}
                    </CardDescription>
                  </CardHeader>
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
                    <div className="flex items-center gap-1.5">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        (STYLE_MAP[script.style]?.bg || '') + ' ' + (STYLE_MAP[script.style]?.color || '')
                      }`}>
                        {STYLE_MAP[script.style]?.label || script.style}
                      </span>
                      {script.product_type && (
                        <span className="px-2 py-0.5 rounded text-xs bg-bg text-muted">
                          {script.product_type}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted shrink-0">
                      <span>❤️ {script.favorited_count}</span>
                      <span>使用 {script.usage_count}</span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
