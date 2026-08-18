import { useCallback, useEffect, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { useToast } from '../../hooks/useToast';
import { adminScenarioApi, type AdminScenario } from '../../services/adminService';

// ----------- Constants -----------

const STATUS_FILTERS = [
  { key: '', label: '全部状态' },
  { key: 'published', label: '已发布' },
  { key: 'draft', label: '草稿' },
];

const CATEGORY_FILTERS = [
  { key: '', label: '全部分类' },
  { key: 'sales_talk', label: '销售话术' },
  { key: 'objection_handling', label: '异议处理' },
  { key: 'product_intro', label: '产品介绍' },
  { key: 'needs_analysis', label: '需求分析' },
  { key: 'closing', label: '促成签单' },
];

const DIFFICULTY_FILTERS = [
  { key: '', label: '全部难度' },
  { key: 'beginner', label: '入门' },
  { key: 'intermediate', label: '进阶' },
  { key: 'advanced', label: '高级' },
];

const DIFFICULTY_VARIANT_MAP: Record<string, 'success' | 'warning' | 'error'> = {
  beginner: 'success',
  intermediate: 'warning',
  advanced: 'error',
};

const DIFFICULTY_LABEL_MAP: Record<string, string> = {
  beginner: '入门',
  intermediate: '进阶',
  advanced: '高级',
};

const STATUS_VARIANT_MAP: Record<string, 'success' | 'default'> = {
  published: 'success',
  draft: 'default',
};

const STATUS_LABEL_MAP: Record<string, string> = {
  published: '已发布',
  draft: '草稿',
};

// ----------- Page -----------

export function TrainingManagePage() {
  const { toast } = useToast();

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 12;

  // Data
  const [scenarios, setScenarios] = useState<AdminScenario[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchScenarios = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminScenarioApi.list({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        difficulty: difficultyFilter || undefined,
        page,
        page_size: pageSize,
      });
      const body = res.data;
      setScenarios(body.data);
      setTotal(body.pagination.total);
      setTotalPages(body.pagination.total_pages);
    } catch {
      setError('加载场景列表失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, categoryFilter, difficultyFilter, page]);

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [statusFilter, categoryFilter, difficultyFilter]);

  const handlePublish = async (scenario: AdminScenario) => {
    setActionLoading(scenario.id);
    try {
      await adminScenarioApi.publish(scenario.id);
      toast({ title: `已发布场景「${scenario.title}」`, variant: 'success' });
      fetchScenarios();
    } catch {
      toast({ title: '发布失败，请重试', variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (scenario: AdminScenario) => {
    if (!window.confirm(`确定要删除场景「${scenario.title}」吗？此操作不可恢复。`)) return;
    setActionLoading(scenario.id);
    try {
      await adminScenarioApi.delete(scenario.id);
      toast({ title: '已删除', variant: 'success' });
      fetchScenarios();
    } catch {
      toast({ title: '删除失败，请重试', variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">陪练场景管理</h1>
            <Badge variant="warning">演示模式</Badge>
          </div>
          <p className="text-muted text-sm mt-1">
            共 {total} 个场景 · 管理AI陪练训练场景
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => toast({ title: '演示模式下暂不支持创建场景', variant: 'warning' })}
        >
          + 创建场景
        </Button>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {/* Status filter pills */}
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setStatusFilter(f.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  statusFilter === f.key
                    ? 'bg-accent text-white'
                    : 'bg-bg text-muted hover:text-text'
                }`}
              >
                {f.label}
              </button>
            ))}

            <span className="text-border mx-1">|</span>

            {/* Category dropdown */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="h-8 rounded-lg border border-border bg-white px-2 text-xs text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              {CATEGORY_FILTERS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>

            {/* Difficulty dropdown */}
            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="h-8 rounded-lg border border-border bg-white px-2 text-xs text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              {DIFFICULTY_FILTERS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Scenario Cards Grid */}
      {loading ? (
        <div className="py-16">
          <LoadingSpinner text="加载场景列表..." />
        </div>
      ) : error ? (
        <div className="py-16 text-center">
          <p className="text-error text-sm mb-3">{error}</p>
          <Button variant="secondary" size="sm" onClick={fetchScenarios}>
            重新加载
          </Button>
        </div>
      ) : scenarios.length === 0 ? (
        <div className="py-16 text-center text-muted text-sm">
          未找到匹配的场景
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {scenarios.map((scenario) => (
              <Card key={scenario.id} padding="md" hover>
                {/* Header: badges */}
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <Badge variant={STATUS_VARIANT_MAP[scenario.status] || 'default'}>
                    {STATUS_LABEL_MAP[scenario.status] || scenario.status}
                  </Badge>
                  <Badge variant={DIFFICULTY_VARIANT_MAP[scenario.difficulty] || 'default'}>
                    {DIFFICULTY_LABEL_MAP[scenario.difficulty] || scenario.difficulty}
                  </Badge>
                </div>

                {/* Title & description */}
                <CardTitle className="text-sm mb-1 line-clamp-1">{scenario.title}</CardTitle>
                <CardDescription className="line-clamp-2 mb-3">
                  {scenario.description}
                </CardDescription>

                {/* Stats */}
                <div className="flex items-center gap-4 text-xs text-muted mb-3">
                  <span className="flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                      <circle cx="9" cy="7" r="4" />
                      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                    </svg>
                    使用 {scenario.usage_count} 次
                  </span>
                  <span className="flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                    </svg>
                    平均 {scenario.avg_score.toFixed(1)} 分
                  </span>
                </div>

                {/* Tags */}
                {scenario.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {scenario.tags.map((tag) => (
                      <Badge key={tag} variant="default">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2 border-t border-border">
                  {scenario.status === 'draft' && (
                    <Button
                      variant="primary"
                      size="sm"
                      loading={actionLoading === scenario.id}
                      onClick={() => handlePublish(scenario)}
                    >
                      发布
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toast({ title: '演示模式下暂不支持编辑', variant: 'warning' })}
                  >
                    编辑
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={actionLoading === scenario.id}
                    onClick={() => handleDelete(scenario)}
                    className="text-error hover:text-error"
                  >
                    删除
                  </Button>
                </div>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
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
        </>
      )}
    </div>
  );
}
