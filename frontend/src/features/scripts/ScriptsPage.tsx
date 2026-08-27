import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Tabs } from '../../components/ui/Tabs';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import {
  BookOpen,
  Check,
  CheckCircle2,
  ChevronLeft,
  Copy,
  FileText,
  Heart,
  MessagesSquare,
  Search,
  Trash2,
} from 'lucide-react';
import {
  streamScriptGenerate,
  getScripts,
  getScript,
  toggleFavorite,
  deleteScript,
  type CustomerContext,
  type Script,
  type ComplianceResult,
  type ComplianceIssue,
  type ScriptCitation,
} from '../../services/scriptService';

// ---- 常量 ----

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'danger' | 'primary' | 'info';

const STYLE_MAP: Record<string, { label: string; variant: BadgeVariant }> = {
  affinity: { label: '亲和型', variant: 'warning' },
  professional: { label: '专业型', variant: 'primary' },
  data_driven: { label: '数据驱动型', variant: 'success' },
  concise: { label: '简洁型', variant: 'info' },
};

/** 统一风格胶囊：生成卡片 / 详情 / 列表三处复用同一 Badge 渲染（语义变体） */
function StyleTag({ styleKey, fallback }: { styleKey: string; fallback?: string }) {
  const meta = STYLE_MAP[styleKey];
  const resolved = meta || STYLE_MAP.professional;
  return <Badge variant={resolved.variant}>{meta?.label || fallback || resolved.label}</Badge>;
}

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
      result.status === 'red' ? 'border-error/30 bg-error/10' :
      result.status === 'yellow' ? 'border-warning/30 bg-warning/10' :
      'border-success/30 bg-success/10'
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
              <p className="text-success pl-1">建议：{issue.suggestion}</p>
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
  citations,
  wordCount,
  isStreaming,
}: {
  style: string;
  content: string;
  compliance: ComplianceResult | null;
  citations?: ScriptCitation[];
  wordCount?: number;
  isStreaming: boolean;
}) {
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
          <StyleTag styleKey={style} />
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
              <Check aria-hidden="true" className="w-4 h-4 text-success" />
            ) : (
              <Copy aria-hidden="true" className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
      <div className={`text-sm leading-relaxed text-text/90 whitespace-pre-wrap ${isStreaming ? '' : ''}`}>
        {content}
        {isStreaming && <span className="inline-block w-1.5 h-4 bg-accent ml-0.5 animate-pulse rounded-sm" />}
      </div>
      {/* RAG 产品知识依据（Citation UI）：生成完成后展示文档标题/章节/来源 */}
      {!isStreaming && citations && citations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <p className="text-xs font-medium text-muted mb-2">
            <BookOpen aria-hidden="true" className="inline h-4 w-4 mr-1 -mt-0.5" />
            <span className="sr-only">📚 </span>产品知识依据（RAG）
          </p>
          <div className="space-y-1.5">
            {citations.map((c, i) => (
              <div key={i} className="text-xs bg-bg/60 rounded-lg p-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-accent font-medium inline-flex items-center gap-1">
                    <FileText aria-hidden="true" className="h-4 w-4 shrink-0" />
                    <span className="sr-only">📄 </span>{c.document_title}
                  </span>
                  {c.section && (
                    <Badge variant="default" className="text-[10px] px-1.5 py-0">{c.section}</Badge>
                  )}
                  {typeof c.score === 'number' && (
                    <span className="text-muted">相关度 {Math.round(c.score * 100)}%</span>
                  )}
                </div>
                {c.source && (
                  <p className="text-muted mt-1 line-clamp-2">「{c.source}」</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
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
  const [genResults, setGenResults] = useState<Record<string, { content: string; compliance: ComplianceResult | null; citations: ScriptCitation[]; wordCount: number; streaming: boolean }>>({});
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
                [s]: { content: '', compliance: null, citations: [], wordCount: 0, streaming: true },
              }));
            });
            break;

          case 'rag_context':
            // RAG知识检索完成（citations 随 style_complete 逐风格带出）
            break;

          case 'style_start':
            setGenResults((prev) => ({
              ...prev,
              [data.style as string]: { content: '', compliance: null, citations: [], wordCount: 0, streaming: true },
            }));
            break;

          case 'token': {
            const style = data.style as string;
            const token = data.content as string;
            setGenResults((prev) => {
              const existing = prev[style] || { content: '', compliance: null, citations: [], wordCount: 0, streaming: true };
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
            const citations = (data.citations as ScriptCitation[]) || [];
            setGenResults((prev) => ({
              ...prev,
              [style]: { content, compliance, citations, wordCount, streaming: false },
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
        <Tabs
          variant="pill"
          active={activeTab}
          onChange={(key) => setActiveTab(key as TabView)}
          items={[
            { key: 'generate', label: '生成话术' },
            { key: 'library', label: '话术库' },
          ]}
        />
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
                  <Select
                    value={genForm.stage}
                    onChange={(e) => setGenForm({ ...genForm, stage: e.target.value })}
                  >
                    {STAGE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">客户异议</label>
                  <Select
                    value={genForm.objection}
                    onChange={(e) => setGenForm({ ...genForm, objection: e.target.value })}
                  >
                    {OBJECTION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">产品类型</label>
                  <Select
                    value={genForm.product_type}
                    onChange={(e) => setGenForm({ ...genForm, product_type: e.target.value })}
                  >
                    <option value="">选择产品</option>
                    {PRODUCT_TYPES.filter((p) => p !== '全部').map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </Select>
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
                        ? 'border-accent bg-accent/10 text-accent'
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
              loading={isGenerating}
              disabled={!genForm.name.trim() || isGenerating}
              onClick={isGenerating ? handleStopGeneration : handleGenerate}
            >
              {isGenerating ? '停止生成' : '生成话术'}
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
              <EmptyState
                icon={<MessagesSquare aria-hidden="true" className="h-5 w-5 text-muted" />}
                title="填写客户信息后，AI将为您生成个性化销售话术"
                description="支持亲和型、专业型、数据驱动型、简洁型四种风格"
              />
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
                citations={result.citations}
                isStreaming={result.streaming}
              />
            ))}

            {genRequestId && !isGenerating && Object.keys(genResults).length > 0 && (
              <div className="text-center py-2">
                <p className="text-xs text-muted">
                  <CheckCircle2 aria-hidden="true" className="inline h-4 w-4 mr-1 -mt-0.5 text-success" />话术生成完成 · 话术已保存至话术库 ·
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
                icon={<Search aria-hidden="true" className="h-4 w-4" />}
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
                <ChevronLeft aria-hidden="true" className="h-4 w-4" />
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
                        <StyleTag styleKey={scriptDetail.style} fallback={scriptDetail.style} />
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
                        className="p-2 rounded-lg hover:bg-bg text-muted hover:text-error transition-colors"
                        title="收藏"
                      >
                        <Heart aria-hidden="true" className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDeleteScript(scriptDetail.id)}
                        className="p-2 rounded-lg hover:bg-error/10 text-muted hover:text-error transition-colors"
                        title="删除"
                      >
                        <Trash2 aria-hidden="true" className="h-5 w-5" />
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
            <EmptyState
              icon={<FileText aria-hidden="true" className="h-5 w-5 text-muted" />}
              title="暂无话术 · 去生成第一条吧"
            />
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
                      <StyleTag styleKey={script.style} fallback={script.style} />
                      {script.product_type && (
                        <span className="px-2 py-0.5 rounded text-xs bg-bg text-muted">
                          {script.product_type}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted shrink-0">
                      <span className="inline-flex items-center gap-1">
                        <Heart aria-hidden="true" className="h-4 w-4 text-error" />
                        {script.favorited_count}
                      </span>
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
