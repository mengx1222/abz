import { useState, useEffect, useCallback } from 'react';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { cn } from '../../utils/cn';
import { useToast } from '../../hooks/useToast';
import { adminScriptApi, type AdminScript } from '../../services/adminService';

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已拒绝' },
];

const styleOptions = [
  { value: '', label: '全部风格' },
  { value: 'professional', label: '专业' },
  { value: 'friendly', label: '亲和' },
  { value: 'concise', label: '简洁' },
  { value: 'persuasive', label: '说服型' },
];

const statusBadgeMap: Record<string, { variant: 'default' | 'success' | 'warning' | 'error'; label: string }> = {
  pending: { variant: 'warning', label: '待审核' },
  approved: { variant: 'success', label: '已通过' },
  rejected: { variant: 'error', label: '已拒绝' },
};

const complianceBadgeMap: Record<string, { className: string; label: string }> = {
  GREEN: { className: 'bg-green-100 text-green-700', label: '合规' },
  YELLOW: { className: 'bg-yellow-100 text-yellow-700', label: '待确认' },
  RED: { className: 'bg-red-100 text-red-700', label: '不合规' },
};

export function ScriptManagePage() {
  const { toast } = useToast();
  const [scripts, setScripts] = useState<AdminScript[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState('');
  const [style, setStyle] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchScripts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await adminScriptApi.list({
        status: status || undefined,
        style: style || undefined,
        page,
        page_size: 10,
      });
      const d = res.data;
      setScripts(d.data);
      setTotalPages(d.pagination.total_pages);
      setTotal(d.pagination.total);
    } catch {
      setError('加载话术列表失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [status, style, page]);

  useEffect(() => {
    fetchScripts();
  }, [fetchScripts]);

  const handleApprove = async (scriptId: string) => {
    setActionLoading(scriptId);
    try {
      await adminScriptApi.approve(scriptId, 'approve');
      toast({ title: '操作成功', description: '话术已通过审核', variant: 'success' });
      fetchScripts();
    } catch {
      toast({ title: '操作失败', description: '审核操作失败，请重试', variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (scriptId: string) => {
    setActionLoading(scriptId);
    try {
      await adminScriptApi.approve(scriptId, 'reject');
      toast({ title: '操作成功', description: '话术已拒绝', variant: 'success' });
      fetchScripts();
    } catch {
      toast({ title: '操作失败', description: '拒绝操作失败，请重试', variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleStatusChange = (val: string) => {
    setStatus(val);
    setPage(1);
  };

  const handleStyleChange = (val: string) => {
    setStyle(val);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">话术管理</h1>
          <p className="text-sm text-muted mt-1">审核与管理 AI 生成的话术内容</p>
        </div>
        <Badge className="bg-amber-100 text-amber-700 w-fit">演示模式</Badge>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-sm text-muted whitespace-nowrap">审核状态</label>
            <select
              value={status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="h-9 rounded-lg border border-border bg-white px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-muted whitespace-nowrap">话术风格</label>
            <select
              value={style}
              onChange={(e) => handleStyleChange(e.target.value)}
              className="h-9 rounded-lg border border-border bg-white px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              {styleOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <span className="text-xs text-muted ml-auto">共 {total.toLocaleString()} 条话术</span>
        </div>
      </Card>

      {/* Table */}
      <Card padding="none" className="overflow-hidden">
        {loading ? (
          <div className="py-12">
            <LoadingSpinner size="md" text="正在加载话术..." />
          </div>
        ) : error ? (
          <div className="text-center py-12 text-muted text-sm">{error}</div>
        ) : scripts.length === 0 ? (
          <div className="text-center py-12 text-muted text-sm">暂无话术记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-bg">
                  <th className="text-left px-4 py-3 font-medium text-muted">标题</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">风格</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">产品类型</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">合规状态</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">作者</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">使用次数</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">审核状态</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">操作</th>
                </tr>
              </thead>
              <tbody>
                {scripts.map((script) => {
                  const sBadge = statusBadgeMap[script.status] || { variant: 'default' as const, label: script.status };
                  const cBadge = complianceBadgeMap[script.compliance_status] || { className: 'bg-gray-100 text-gray-600', label: script.compliance_status };
                  const isActionLoading = actionLoading === script.id;

                  return (
                    <tr key={script.id} className="border-b border-border last:border-b-0 hover:bg-bg/50 transition-colors">
                      <td className="px-4 py-3 text-text font-medium max-w-[200px] truncate">
                        {script.title}
                      </td>
                      <td className="px-4 py-3">
                        <Badge>{script.style_label || script.style}</Badge>
                      </td>
                      <td className="px-4 py-3 text-muted">{script.product_type}</td>
                      <td className="px-4 py-3">
                        <Badge className={cBadge.className}>{cBadge.label}</Badge>
                      </td>
                      <td className="px-4 py-3 text-text">{script.author_name}</td>
                      <td className="px-4 py-3 text-muted">{script.usage_count}</td>
                      <td className="px-4 py-3">
                        <Badge variant={sBadge.variant}>{sBadge.label}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {(script.status === 'pending' || script.status === 'rejected') && (
                            <Button
                              variant="primary"
                              size="sm"
                              className="bg-success hover:bg-success/90"
                              loading={isActionLoading}
                              onClick={() => handleApprove(script.id)}
                            >
                              通过
                            </Button>
                          )}
                          {(script.status === 'pending' || script.status === 'approved') && (
                            <Button
                              variant="danger"
                              size="sm"
                              loading={isActionLoading}
                              onClick={() => handleReject(script.id)}
                            >
                              拒绝
                            </Button>
                          )}
                          {script.status === 'approved' && script.status !== 'pending' && script.status !== 'rejected' && (
                            <span className="text-xs text-muted">--</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && !error && scripts.length > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border">
            <p className="text-sm text-muted">
              第 {page} / {totalPages} 页
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                上一页
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                下一页
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
