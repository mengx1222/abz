import { useCallback, useEffect, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { useToast } from '../../hooks/useToast';
import { complianceApi, type ComplianceRule, type ComplianceReview } from '../../services/adminService';
import { cn } from '../../utils/cn';

// ----------- Constants -----------

type TabKey = 'rules' | 'reviews';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'rules', label: '合规规则' },
  { key: 'reviews', label: '审核列表' },
];

const SEVERITY_VARIANT_MAP: Record<string, 'error' | 'warning' | 'default'> = {
  violation: 'error',
  warning: 'warning',
  info: 'default',
};

const REVIEW_STATUS_VARIANT_MAP: Record<string, 'warning' | 'success' | 'error'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'error',
};

const REVIEW_STATUS_LABEL_MAP: Record<string, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回',
};

const PRIORITY_VARIANT_MAP: Record<string, 'error' | 'warning' | 'default'> = {
  high: 'error',
  medium: 'warning',
  low: 'default',
};

const PRIORITY_LABEL_MAP: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
};

// ----------- Page -----------

export function CompliancePage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<TabKey>('rules');

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-text">合规中心</h1>
          <Badge variant="warning">演示模式</Badge>
        </div>
        <p className="text-muted text-sm mt-1">
          管理合规规则与内容审核
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'px-4 py-2.5 text-sm font-medium transition-colors cursor-pointer border-b-2 -mb-px',
              activeTab === tab.key
                ? 'text-accent border-accent'
                : 'text-muted border-transparent hover:text-text'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'rules' ? <RulesTab /> : <ReviewsTab />}
    </div>
  );
}

// ----------- Rules Tab -----------

function RulesTab() {
  const { toast } = useToast();
  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const fetchRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await complianceApi.listRules();
      setRules(res.data.data);
    } catch {
      setError('加载合规规则失败，请重试');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleToggleActive = async (rule: ComplianceRule) => {
    setTogglingId(rule.id);
    try {
      await complianceApi.updateRule(rule.id, { is_active: !rule.is_active });
      toast({
        title: rule.is_active ? `已停用规则「${rule.name}」` : `已启用规则「${rule.name}」`,
        variant: 'success',
      });
      fetchRules();
    } catch {
      toast({ title: '操作失败，请重试', variant: 'error' });
    } finally {
      setTogglingId(null);
    }
  };

  if (loading) {
    return (
      <div className="py-16">
        <LoadingSpinner text="加载合规规则..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-16 text-center">
        <p className="text-error text-sm mb-3">{error}</p>
        <Button variant="secondary" size="sm" onClick={fetchRules}>
          重新加载
        </Button>
      </div>
    );
  }

  if (rules.length === 0) {
    return (
      <div className="py-16 text-center text-muted text-sm">
        暂无合规规则
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {rules.map((rule) => (
        <Card key={rule.id} padding="md">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2 min-w-0">
              <CardTitle className="text-sm truncate">{rule.name}</CardTitle>
              <Badge variant={SEVERITY_VARIANT_MAP[rule.severity] || 'default'}>
                {rule.severity_label}
              </Badge>
            </div>
            <button
              onClick={() => handleToggleActive(rule)}
              disabled={togglingId === rule.id}
              className={cn(
                'ml-2 relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed',
                rule.is_active ? 'bg-success' : 'bg-border'
              )}
            >
              <span
                className={cn(
                  'pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200',
                  rule.is_active ? 'translate-x-4' : 'translate-x-0'
                )}
              />
            </button>
          </div>
          <CardDescription className="mb-3 line-clamp-2">{rule.description}</CardDescription>
          <div className="flex flex-wrap gap-1.5">
            {rule.keywords.map((kw) => (
              <Badge key={kw} variant="default">
                {kw}
              </Badge>
            ))}
          </div>
          <div className="mt-3 pt-2 border-t border-border flex items-center justify-between">
            <span className="text-xs text-muted">分类：{rule.category}</span>
            <Badge variant={rule.is_active ? 'success' : 'default'}>
              {rule.is_active ? '已启用' : '已停用'}
            </Badge>
          </div>
        </Card>
      ))}
    </div>
  );
}

// ----------- Reviews Tab -----------

function ReviewsTab() {
  const { toast } = useToast();
  const [reviews, setReviews] = useState<ComplianceReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await complianceApi.listReviews({ page, page_size: 20 });
      const body = res.data;
      setReviews(body.data);
      setTotalPages(body.pagination.total_pages);
    } catch {
      setError('加载审核列表失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const handleProcessReview = async (reviewId: string, action: 'approve' | 'reject') => {
    setActionLoading(reviewId);
    try {
      const comment = action === 'approve' ? '审核通过' : '审核未通过';
      await complianceApi.processReview(reviewId, action, comment);
      toast({
        title: action === 'approve' ? '已通过审核' : '已驳回内容',
        variant: 'success',
      });
      fetchReviews();
    } catch {
      toast({ title: '操作失败，请重试', variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="py-16">
        <LoadingSpinner text="加载审核列表..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-16 text-center">
        <p className="text-error text-sm mb-3">{error}</p>
        <Button variant="secondary" size="sm" onClick={fetchReviews}>
          重新加载
        </Button>
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="py-16 text-center text-muted text-sm">
        暂无待审核内容
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {reviews.map((review) => (
        <Card key={review.id} padding="md">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              {/* Title row with badges */}
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <Badge variant="default">{review.type_label}</Badge>
                <Badge variant={SEVERITY_VARIANT_MAP[review.severity] || 'default'}>
                  {review.severity === 'violation' ? '违规' : review.severity === 'warning' ? '警告' : '提示'}
                </Badge>
                <Badge variant={REVIEW_STATUS_VARIANT_MAP[review.status] || 'default'}>
                  {REVIEW_STATUS_LABEL_MAP[review.status] || review.status}
                </Badge>
                <Badge variant={PRIORITY_VARIANT_MAP[review.priority] || 'default'}>
                  {PRIORITY_LABEL_MAP[review.priority] || review.priority}
                </Badge>
              </div>

              {/* Title & preview */}
              <h4 className="text-sm font-medium text-text mb-1 truncate">{review.title}</h4>
              <p className="text-xs text-muted line-clamp-2 mb-2">{review.content_preview}</p>

              {/* Author & time */}
              <p className="text-xs text-muted">
                作者：{review.author_name}
                {review.created_at && (
                  <>
                    {' · '}
                    {new Date(review.created_at).toLocaleString('zh-CN', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </>
                )}
              </p>
            </div>

            {/* Actions */}
            {review.status === 'pending' && (
              <div className="flex items-center gap-2 shrink-0">
                <Button
                  variant="primary"
                  size="sm"
                  loading={actionLoading === review.id}
                  onClick={() => handleProcessReview(review.id, 'approve')}
                  className="!bg-success hover:!bg-success/90 active:!bg-success/80"
                >
                  通过
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  loading={actionLoading === review.id}
                  onClick={() => handleProcessReview(review.id, 'reject')}
                >
                  驳回
                </Button>
              </div>
            )}
          </div>
        </Card>
      ))}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            上一页
          </Button>
          <span className="text-sm text-muted">
            {page} / {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </Button>
        </div>
      )}
    </div>
  );
}
