import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { Avatar } from '../../components/ui/Avatar';
import { useToast } from '../../hooks/useToast';
import {
  getCustomer,
  addInteraction,
  addFollowup,
  analyzeCustomerSSE,
  type CustomerDetail,
  type AnalysisResult,
  type InteractionCreate,
  type FollowupCreate,
} from '../../services/customerService';

// ----------- Constants -----------

const STAGE_MAP: Record<
  string,
  { label: string; variant: 'default' | 'warning' | 'success' | 'error' }
> = {
  initial_contact: { label: '初步接触', variant: 'default' },
  needs_analysis: { label: '需求分析', variant: 'default' },
  proposal: { label: '方案推荐', variant: 'warning' },
  presentation: { label: '方案展示', variant: 'warning' },
  negotiation: { label: '谈判中', variant: 'warning' },
  closed_won: { label: '已签单', variant: 'success' },
  closed_lost: { label: '已流失', variant: 'error' },
};

const TYPE_MAP: Record<string, string> = {
  prospective: '准客户',
  active: '活跃客户',
  lapsed: '流失客户',
};

const GENDER_MAP: Record<string, string> = {
  male: '男',
  female: '女',
};

const INTERACTION_TYPE_MAP: Record<string, string> = {
  phone: '电话',
  wechat: '微信',
  f2f: '面谈',
  email: '邮件',
  other: '其他',
};

const FOLLOWUP_STATUS_MAP: Record<
  string,
  { label: string; variant: 'default' | 'success' | 'warning' | 'error' }
> = {
  pending: { label: '待完成', variant: 'warning' },
  completed: { label: '已完成', variant: 'success' },
  cancelled: { label: '已取消', variant: 'default' },
};

const PRICE_SENSITIVITY_MAP: Record<
  string,
  { label: string; variant: 'success' | 'warning' | 'error' }
> = {
  low: { label: '低', variant: 'success' },
  medium: { label: '中', variant: 'warning' },
  high: { label: '高', variant: 'error' },
};

type TabKey = 'info' | 'interactions' | 'followups' | 'analysis';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'info', label: '基本信息' },
  { key: 'interactions', label: '互动记录' },
  { key: 'followups', label: '跟进任务' },
  { key: 'analysis', label: 'AI 分析' },
];

// ----------- Helpers -----------

function maskPhone(phone: string | null): string {
  if (!phone || phone.length < 7) return phone ?? '-';
  return phone.slice(0, 3) + '****' + phone.slice(-4);
}

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

function StarRating({ level, max = 5 }: { level: number; max?: number }) {
  return (
    <span className="inline-flex gap-0.5">
      {Array.from({ length: max }, (_, i) => (
        <svg
          key={i}
          className={`w-4 h-4 ${i < level ? 'text-warning' : 'text-border'}`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ))}
    </span>
  );
}

function InfoField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-muted mb-1">{label}</p>
      <p className="text-sm text-text">{value || '-'}</p>
    </div>
  );
}

// ----------- Interaction Form -----------

function InteractionForm({
  onSubmit,
  onCancel,
  loading,
}: {
  onSubmit: (data: InteractionCreate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [type, setType] = useState<InteractionCreate['type']>('phone');
  const [direction, setDirection] = useState<InteractionCreate['direction']>('outbound');
  const [content, setContent] = useState('');
  const [outcome, setOutcome] = useState('');

  const fieldClass =
    'w-full h-10 rounded-lg border border-border bg-white px-3 text-sm text-text placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent';
  const selectClass = fieldClass;
  const labelClass = 'text-sm font-medium text-text mb-1.5 block';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ type, direction, content: content || null, outcome: outcome || null });
  };

  return (
    <Card padding="md" className="border-accent/30">
      <form onSubmit={handleSubmit} className="space-y-3">
        <h4 className="text-sm font-semibold text-text">添加互动记录</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>互动方式</label>
            <select
              className={selectClass}
              value={type}
              onChange={(e) => setType(e.target.value as InteractionCreate['type'])}
            >
              {Object.entries(INTERACTION_TYPE_MAP).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>方向</label>
            <select
              className={selectClass}
              value={direction}
              onChange={(e) => setDirection(e.target.value as InteractionCreate['direction'])}
            >
              <option value="outbound">呼出</option>
              <option value="inbound">呼入</option>
            </select>
          </div>
        </div>
        <div>
          <label className={labelClass}>沟通内容</label>
          <textarea
            className={fieldClass + ' h-20 resize-none'}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="记录沟通要点..."
          />
        </div>
        <div>
          <label className={labelClass}>沟通结果</label>
          <textarea
            className={fieldClass + ' h-16 resize-none'}
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
            placeholder="沟通结果与下一步计划..."
          />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" size="sm" type="button" onClick={onCancel}>
            取消
          </Button>
          <Button variant="primary" size="sm" type="submit" loading={loading}>
            提交
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ----------- Followup Form -----------

function FollowupForm({
  onSubmit,
  onCancel,
  loading,
}: {
  onSubmit: (data: FollowupCreate) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [scheduledDate, setScheduledDate] = useState('');
  const [content, setContent] = useState('');
  const [status, setStatus] = useState<FollowupCreate['status']>('pending');

  const fieldClass =
    'w-full h-10 rounded-lg border border-border bg-white px-3 text-sm text-text placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent';
  const selectClass = fieldClass;
  const labelClass = 'text-sm font-medium text-text mb-1.5 block';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduledDate) return;
    onSubmit({
      scheduled_date: scheduledDate,
      content: content || null,
      status,
    });
  };

  return (
    <Card padding="md" className="border-accent/30">
      <form onSubmit={handleSubmit} className="space-y-3">
        <h4 className="text-sm font-semibold text-text">添加跟进任务</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>计划日期</label>
            <input
              type="date"
              className={fieldClass}
              value={scheduledDate}
              onChange={(e) => setScheduledDate(e.target.value)}
              required
            />
          </div>
          <div>
            <label className={labelClass}>状态</label>
            <select
              className={selectClass}
              value={status}
              onChange={(e) => setStatus(e.target.value as FollowupCreate['status'])}
            >
              <option value="pending">待完成</option>
              <option value="completed">已完成</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>
        </div>
        <div>
          <label className={labelClass}>跟进内容</label>
          <textarea
            className={fieldClass + ' h-20 resize-none'}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="跟进计划详情..."
          />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" size="sm" type="button" onClick={onCancel}>
            取消
          </Button>
          <Button variant="primary" size="sm" type="submit" loading={loading}>
            提交
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ----------- Main Page -----------

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  // Data
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tabs
  const [activeTab, setActiveTab] = useState<TabKey>('info');

  // Forms
  const [showInteractionForm, setShowInteractionForm] = useState(false);
  const [submittingInteraction, setSubmittingInteraction] = useState(false);
  const [showFollowupForm, setShowFollowupForm] = useState(false);
  const [submittingFollowup, setSubmittingFollowup] = useState(false);

  // AI Analysis
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisText, setAnalysisText] = useState('');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const analysisRef = useRef<HTMLDivElement>(null);

  const fetchCustomer = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const data = await getCustomer(id);
      setCustomer(data);
    } catch (err: unknown) {
      if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        (err as { response?: { status?: number } }).response?.status === 404
      ) {
        setNotFound(true);
      } else {
        setError('加载客户信息失败，请重试');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchCustomer();
  }, [fetchCustomer]);

  // Auto-scroll analysis text
  useEffect(() => {
    if (analysisRef.current) {
      analysisRef.current.scrollTop = analysisRef.current.scrollHeight;
    }
  }, [analysisText]);

  // ----------- Handlers -----------

  const handleAddInteraction = async (data: InteractionCreate) => {
    if (!id) return;
    setSubmittingInteraction(true);
    try {
      await addInteraction(id, data);
      toast({ title: '互动记录已添加', variant: 'success' });
      setShowInteractionForm(false);
      fetchCustomer();
    } catch {
      toast({ title: '添加失败', variant: 'error' });
    } finally {
      setSubmittingInteraction(false);
    }
  };

  const handleAddFollowup = async (data: FollowupCreate) => {
    if (!id) return;
    setSubmittingFollowup(true);
    try {
      await addFollowup(id, data);
      toast({ title: '跟进任务已添加', variant: 'success' });
      setShowFollowupForm(false);
      fetchCustomer();
    } catch {
      toast({ title: '添加失败', variant: 'error' });
    } finally {
      setSubmittingFollowup(false);
    }
  };

  const handleStartAnalysis = async () => {
    if (!id || analyzing) return;
    setAnalyzing(true);
    setAnalysisText('');
    setAnalysisResult(null);
    setAnalysisError(null);
    setActiveTab('analysis');

    try {
      for await (const event of analyzeCustomerSSE(id)) {
        if (event.event === 'token') {
          const token = (event.data?.token as string) || '';
          setAnalysisText((prev) => prev + token);
        } else if (event.event === 'structured_data') {
          setAnalysisResult(event.data as unknown as AnalysisResult);
        } else if (event.event === 'error') {
          const msg = (event.data?.message as string) || '分析失败';
          setAnalysisError(msg);
        }
      }
    } catch (err) {
      setAnalysisError(
        err instanceof Error ? err.message : 'AI 分析请求失败',
      );
    } finally {
      setAnalyzing(false);
    }
  };

  // ----------- Loading / Error / 404 States -----------

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-16">
        <LoadingSpinner text="加载客户信息..." />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <p className="text-muted text-lg mb-4">未找到该客户</p>
        <Button variant="secondary" size="sm" onClick={() => navigate('/customers')}>
          返回客户列表
        </Button>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <p className="text-error text-sm mb-4">{error || '客户数据异常'}</p>
        <Button variant="secondary" size="sm" onClick={fetchCustomer}>
          重新加载
        </Button>
      </div>
    );
  }

  const stage = STAGE_MAP[customer.current_stage];
  const typeLabel = TYPE_MAP[customer.customer_type] || customer.customer_type;

  // ----------- Render -----------

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Back + Header */}
      <div className="space-y-3">
        <button
          onClick={() => navigate('/customers')}
          className="text-sm text-muted hover:text-text transition-colors cursor-pointer inline-flex items-center gap-1"
        >
          <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z" clipRule="evenodd" />
          </svg>
          返回列表
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <Avatar name={customer.name} size="lg" />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-text">{customer.name}</h1>
                {customer.age && (
                  <span className="text-sm text-muted">
                    {customer.age}岁
                  </span>
                )}
                {customer.gender && (
                  <span className="text-sm text-muted">
                    {GENDER_MAP[customer.gender] || customer.gender}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1">
                {stage && <Badge variant={stage.variant}>{stage.label}</Badge>}
                <Badge variant="default">{typeLabel}</Badge>
              </div>
            </div>
          </div>

          <div className="flex gap-2 flex-wrap">
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate(`/sales-agent/${customer.id}`)}
            >
              AI 销售副驾
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowInteractionForm(true)}
            >
              添加互动
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowFollowupForm(true)}
            >
              添加跟进
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleStartAnalysis}
              loading={analyzing}
            >
              AI分析
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors cursor-pointer border-b-2 -mb-px ${
              activeTab === tab.key
                ? 'text-accent border-accent'
                : 'text-muted border-transparent hover:text-text'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'info' && <InfoTab customer={customer} />}
      {activeTab === 'interactions' && (
        <InteractionsTab
          interactions={customer.interactions}
          showForm={showInteractionForm}
          onCancelForm={() => setShowInteractionForm(false)}
          onSubmitForm={handleAddInteraction}
          submittingForm={submittingInteraction}
        />
      )}
      {activeTab === 'followups' && (
        <FollowupsTab
          followups={customer.followups}
          showForm={showFollowupForm}
          onCancelForm={() => setShowFollowupForm(false)}
          onSubmitForm={handleAddFollowup}
          submittingForm={submittingFollowup}
        />
      )}
      {activeTab === 'analysis' && (
        <AnalysisTab
          analysisText={analysisText}
          analysisResult={analysisResult}
          analyzing={analyzing}
          analysisError={analysisError}
          onStart={handleStartAnalysis}
          scrollRef={analysisRef}
        />
      )}
    </div>
  );
}

// ============ Tab Components ============

// ----------- Info Tab -----------

function InfoTab({ customer }: { customer: CustomerDetail }) {
  const stage = STAGE_MAP[customer.current_stage];

  return (
    <Card padding="lg">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-5">
        <InfoField label="姓名" value={customer.name} />
        <InfoField label="年龄" value={customer.age ? `${customer.age}岁` : null} />
        <InfoField
          label="性别"
          value={customer.gender ? GENDER_MAP[customer.gender] : null}
        />
        <InfoField label="手机号" value={maskPhone(customer.phone)} />
        <InfoField
          label="客户类型"
          value={TYPE_MAP[customer.customer_type]}
        />
        <InfoField
          label="当前阶段"
          value={
            stage ? (
              <Badge variant={stage.variant}>{stage.label}</Badge>
            ) : null
          }
        />
        <InfoField
          label="意向等级"
          value={<StarRating level={customer.intention_level} />}
        />
        <InfoField label="来源渠道" value={customer.source_channel} />
        <InfoField label="感兴趣险种" value={customer.insurance_type} />
        <InfoField
          label="标签"
          value={
            customer.tags && customer.tags.length > 0 ? (
              <div className="flex gap-1 flex-wrap">
                {customer.tags.map((tag) => (
                  <Badge key={tag} variant="default">
                    {tag}
                  </Badge>
                ))}
              </div>
            ) : null
          }
        />
        <InfoField label="负责人" value={customer.assigned_to} />
        <InfoField label="创建时间" value={formatDateTime(customer.created_at)} />
        <InfoField label="更新时间" value={formatDateTime(customer.updated_at)} />
      </div>
      {customer.notes && (
        <div className="mt-6 pt-4 border-t border-border">
          <p className="text-xs text-muted mb-1">备注</p>
          <p className="text-sm text-text whitespace-pre-wrap">{customer.notes}</p>
        </div>
      )}
    </Card>
  );
}

// ----------- Interactions Tab -----------

function InteractionsTab({
  interactions,
  showForm,
  onCancelForm,
  onSubmitForm,
  submittingForm,
}: {
  interactions: CustomerDetail['interactions'];
  showForm: boolean;
  onCancelForm: () => void;
  onSubmitForm: (data: InteractionCreate) => void;
  submittingForm: boolean;
}) {
  return (
    <div className="space-y-3">
      {!showForm && (
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {}}  // handled by parent
          style={{ display: 'none' }}
        >
          添加互动记录
        </Button>
      )}

      {showForm && (
        <InteractionForm
          onSubmit={onSubmitForm}
          onCancel={onCancelForm}
          loading={submittingForm}
        />
      )}

      {interactions.length === 0 && !showForm ? (
        <Card padding="md">
          <p className="text-center text-muted text-sm py-8">暂无互动记录</p>
        </Card>
      ) : (
        <div className="relative pl-6 border-l-2 border-border space-y-4">
          {interactions.map((item) => (
            <div key={item.id} className="relative">
              {/* Timeline dot */}
              <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-accent/20 border-2 border-accent flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-accent" />
              </div>

              <Card padding="md">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-medium text-text">
                    {INTERACTION_TYPE_MAP[item.type] || item.type}
                  </span>
                  <Badge
                    variant={item.direction === 'inbound' ? 'success' : 'default'}
                  >
                    {item.direction === 'inbound' ? '呼入' : '呼出'}
                  </Badge>
                  <span className="text-xs text-muted ml-auto">
                    {formatDateTime(item.created_at)}
                  </span>
                </div>
                {item.content && (
                  <p className="text-sm text-text mb-1">{item.content}</p>
                )}
                {item.outcome && (
                  <p className="text-sm text-muted">{item.outcome}</p>
                )}
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ----------- Followups Tab -----------

function FollowupsTab({
  followups,
  showForm,
  onCancelForm,
  onSubmitForm,
  submittingForm,
}: {
  followups: CustomerDetail['followups'];
  showForm: boolean;
  onCancelForm: () => void;
  onSubmitForm: (data: FollowupCreate) => void;
  submittingForm: boolean;
}) {
  return (
    <div className="space-y-3">
      {showForm && (
        <FollowupForm
          onSubmit={onSubmitForm}
          onCancel={onCancelForm}
          loading={submittingForm}
        />
      )}

      {followups.length === 0 && !showForm ? (
        <Card padding="md">
          <p className="text-center text-muted text-sm py-8">暂无跟进任务</p>
        </Card>
      ) : (
        <div className="grid gap-3">
          {followups.map((item) => {
            const statusInfo = FOLLOWUP_STATUS_MAP[item.status];
            return (
              <Card key={item.id} padding="md">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-text">
                        {formatDate(item.scheduled_date)}
                      </span>
                      {statusInfo && (
                        <Badge variant={statusInfo.variant}>
                          {statusInfo.label}
                        </Badge>
                      )}
                    </div>
                    {item.content && (
                      <p className="text-sm text-text">{item.content}</p>
                    )}
                    {item.result && (
                      <p className="text-sm text-muted">{item.result}</p>
                    )}
                  </div>
                  {item.completed_date && (
                    <span className="text-xs text-muted whitespace-nowrap">
                      完成: {formatDate(item.completed_date)}
                    </span>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ----------- Analysis Tab -----------

function AnalysisTab({
  analysisText,
  analysisResult,
  analyzing,
  analysisError,
  onStart,
  scrollRef,
}: {
  analysisText: string;
  analysisResult: AnalysisResult | null;
  analyzing: boolean;
  analysisError: string | null;
  onStart: () => void;
  scrollRef: React.RefObject<HTMLDivElement | null>;
}) {
  const hasContent = analysisText || analysisResult;

  return (
    <div className="space-y-4">
      {!hasContent && !analyzing && !analysisError && (
        <Card padding="lg" className="text-center">
          <p className="text-muted text-sm mb-4">
            使用 AI 对客户进行全面分析，获取画像、购买意向、推荐产品等洞察
          </p>
          <Button variant="primary" size="md" onClick={onStart}>
            开始 AI 分析
          </Button>
        </Card>
      )}

      {/* Loading indicator */}
      {analyzing && !analysisText && (
        <Card padding="md">
          <div className="flex items-center gap-3">
            <LoadingSpinner size="sm" />
            <p className="text-sm text-muted">正在分析客户数据...</p>
          </div>
        </Card>
      )}

      {/* Streaming text */}
      {analysisText && (
        <Card padding="md">
          <p className="text-xs text-muted mb-2">AI分析 / 仅供业务辅助</p>
          <div
            ref={scrollRef}
            className="text-sm text-text whitespace-pre-wrap max-h-60 overflow-y-auto"
          >
            {analysisText}
            {analyzing && (
              <span className="inline-block w-1.5 h-4 bg-accent animate-pulse ml-0.5 align-middle" />
            )}
          </div>
        </Card>
      )}

      {/* Structured data */}
      {analysisResult && (
        <div className="space-y-4">
          {/* Customer Profile */}
          <Card padding="md">
            <p className="text-xs text-muted mb-2">AI分析 / 仅供业务辅助</p>
            <h4 className="text-sm font-semibold text-text mb-2">客户画像</h4>
            <p className="text-sm text-text whitespace-pre-wrap">
              {analysisResult.customer_profile}
            </p>
          </Card>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Purchase Intent */}
            <Card padding="md">
              <p className="text-xs text-muted mb-2">AI分析 / 仅供业务辅助</p>
              <h4 className="text-sm font-semibold text-text mb-2">购买意向</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted">意向评分</span>
                  <span className="font-medium text-text">
                    {analysisResult.purchase_intent}/10
                  </span>
                </div>
                <div className="w-full h-2.5 bg-bg rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500"
                    style={{ width: `${analysisResult.purchase_intent * 10}%` }}
                  />
                </div>
              </div>
            </Card>

            {/* Price Sensitivity */}
            <Card padding="md">
              <p className="text-xs text-muted mb-2">AI分析 / 仅供业务辅助</p>
              <h4 className="text-sm font-semibold text-text mb-2">价格敏感度</h4>
              <div>
                <Badge
                  variant={
                    PRICE_SENSITIVITY_MAP[analysisResult.price_sensitivity]?.variant ||
                    'default'
                  }
                >
                  {PRICE_SENSITIVITY_MAP[analysisResult.price_sensitivity]?.label ||
                    analysisResult.price_sensitivity}
                </Badge>
              </div>
            </Card>
          </div>

          {/* Recommended Products */}
          {analysisResult.recommended_products.length > 0 && (
            <Card padding="md">
              <p className="text-xs text-muted mb-2">AI分析 / 仅供业务辅助</p>
              <h4 className="text-sm font-semibold text-text mb-3">推荐产品</h4>
              <ul className="space-y-1.5">
                {analysisResult.recommended_products.map((product, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-text">
                    <span className="text-accent mt-0.5 flex-shrink-0">--</span>
                    {product}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Recommended Actions */}
          {analysisResult.recommended_actions.length > 0 && (
            <Card padding="md">
              <p className="text-xs text-muted mb-2">AI分析 / 仅供业务辅助</p>
              <h4 className="text-sm font-semibold text-text mb-3">建议行动</h4>
              <ol className="space-y-1.5">
                {analysisResult.recommended_actions.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-text">
                    <span className="text-success font-medium mt-0.5 flex-shrink-0">
                      {idx + 1}.
                    </span>
                    <svg
                      className="w-4 h-4 text-success flex-shrink-0 mt-0.5"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {action}
                  </li>
                ))}
              </ol>
            </Card>
          )}

          {/* Forbidden Actions */}
          {analysisResult.forbidden_actions.length > 0 && (
            <Card padding="md">
              <p className="text-xs text-muted mb-2">AI分析 / 仅供业务辅助</p>
              <h4 className="text-sm font-semibold text-text mb-3">禁忌事项</h4>
              <ol className="space-y-1.5">
                {analysisResult.forbidden_actions.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-text">
                    <span className="text-error font-medium mt-0.5 flex-shrink-0">
                      {idx + 1}.
                    </span>
                    <svg
                      className="w-4 h-4 text-error flex-shrink-0 mt-0.5"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {action}
                  </li>
                ))}
              </ol>
            </Card>
          )}

          {/* Risk Notes */}
          {analysisResult.risk_notes.length > 0 && (
            <Card padding="md">
              <p className="text-xs text-muted mb-2">AI分析 / 仅供业务辅助</p>
              <h4 className="text-sm font-semibold text-text mb-3">风险提示</h4>
              <div className="flex flex-wrap gap-2">
                {analysisResult.risk_notes.map((note, idx) => (
                  <Badge key={idx} variant="warning">
                    {note}
                  </Badge>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Error */}
      {analysisError && (
        <Card padding="md">
          <p className="text-sm text-error">{analysisError}</p>
        </Card>
      )}
    </div>
  );
}
