import { useState, useEffect, useCallback } from 'react';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { cn } from '../../utils/cn';
import { auditLogApi, type AuditLog } from '../../services/adminService';

const actionOptions = [
  { value: '', label: '全部操作' },
  { value: 'login', label: '登录' },
  { value: 'customer.view', label: '查看客户' },
  { value: 'customer.create', label: '创建客户' },
  { value: 'customer.update', label: '更新客户' },
  { value: 'ai.product_qa', label: 'AI 产品问答' },
  { value: 'ai.script_generate', label: 'AI 话术生成' },
  { value: 'script.generate', label: '生成话术' },
  { value: 'script.approve', label: '审批话术' },
  { value: 'training.start', label: '开始培训' },
  { value: 'training.complete', label: '完成培训' },
  { value: 'community.post', label: '发布帖子' },
  { value: 'community.comment', label: '发表评论' },
  { value: 'compliance.check', label: '合规检查' },
  { value: 'knowledge.upload', label: '上传知识' },
];

const resourceOptions = [
  { value: '', label: '全部类型' },
  { value: 'user', label: '用户' },
  { value: 'customer', label: '客户' },
  { value: 'script', label: '话术' },
  { value: 'training', label: '培训' },
  { value: 'community', label: '社区' },
  { value: 'compliance', label: '合规' },
  { value: 'knowledge', label: '知识库' },
];

const pageSizeOptions = [10, 20, 50];

const actionBadgeMap: Record<string, { className: string; label: string }> = {
  login: { className: 'bg-blue-100 text-blue-700', label: '登录' },
  'customer.view': { className: 'bg-green-100 text-green-700', label: '查看客户' },
  'customer.create': { className: 'bg-green-100 text-green-700', label: '创建客户' },
  'customer.update': { className: 'bg-green-100 text-green-700', label: '更新客户' },
  'ai.product_qa': { className: 'bg-purple-100 text-purple-700', label: 'AI产品问答' },
  'ai.script_generate': { className: 'bg-purple-100 text-purple-700', label: 'AI话术生成' },
  'script.generate': { className: 'bg-orange-100 text-orange-700', label: '生成话术' },
  'script.approve': { className: 'bg-orange-100 text-orange-700', label: '审批话术' },
  'training.start': { className: 'bg-cyan-100 text-cyan-700', label: '开始培训' },
  'training.complete': { className: 'bg-cyan-100 text-cyan-700', label: '完成培训' },
  'community.post': { className: 'bg-pink-100 text-pink-700', label: '发布帖子' },
  'community.comment': { className: 'bg-pink-100 text-pink-700', label: '发表评论' },
  'compliance.check': { className: 'bg-red-100 text-red-700', label: '合规检查' },
  'knowledge.upload': { className: 'bg-teal-100 text-teal-700', label: '上传知识' },
};

function getActionBadge(action: string) {
  return actionBadgeMap[action] || { className: 'bg-gray-100 text-gray-600', label: action };
}

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function AuditLogPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [action, setAction] = useState('');
  const [resourceType, setResourceType] = useState('');
  const [pageSize, setPageSize] = useState(10);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await auditLogApi.list({
        action: action || undefined,
        resource_type: resourceType || undefined,
        page,
        page_size: pageSize,
      });
      const d = res.data;
      setLogs(d.data);
      setTotalPages(d.pagination.total_pages);
      setTotal(d.pagination.total);
    } catch {
      setError('加载审计日志失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [action, resourceType, page, pageSize]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleActionChange = (val: string) => {
    setAction(val);
    setPage(1);
  };

  const handleResourceChange = (val: string) => {
    setResourceType(val);
    setPage(1);
  };

  const handlePageSizeChange = (val: string) => {
    setPageSize(Number(val));
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">审计日志</h1>
          <p className="text-sm text-muted mt-1">查看系统操作记录</p>
        </div>
        <Badge className="bg-amber-100 text-amber-700 w-fit">演示模式</Badge>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-sm text-muted whitespace-nowrap">操作类型</label>
            <select
              value={action}
              onChange={(e) => handleActionChange(e.target.value)}
              className="h-9 rounded-lg border border-border bg-white px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              {actionOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-muted whitespace-nowrap">资源类型</label>
            <select
              value={resourceType}
              onChange={(e) => handleResourceChange(e.target.value)}
              className="h-9 rounded-lg border border-border bg-white px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              {resourceOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-muted whitespace-nowrap">每页条数</label>
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(e.target.value)}
              className="h-9 rounded-lg border border-border bg-white px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              {pageSizeOptions.map((s) => (
                <option key={s} value={s}>
                  {s} 条
                </option>
              ))}
            </select>
          </div>

          <span className="text-xs text-muted ml-auto">共 {total.toLocaleString()} 条记录</span>
        </div>
      </Card>

      {/* Table */}
      <Card padding="none" className="overflow-hidden">
        {loading ? (
          <div className="py-12">
            <LoadingSpinner size="md" text="正在加载日志..." />
          </div>
        ) : error ? (
          <div className="text-center py-12 text-muted text-sm">{error}</div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12 text-muted text-sm">暂无审计日志记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-bg">
                  <th className="text-left px-4 py-3 font-medium text-muted">时间</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">用户</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">操作</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">资源类型</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">描述</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">IP 地址</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => {
                  const badge = getActionBadge(log.action);
                  return (
                    <tr key={log.id} className="border-b border-border last:border-b-0 hover:bg-bg/50 transition-colors">
                      <td className="px-4 py-3 text-muted whitespace-nowrap">{formatTime(log.created_at)}</td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-text font-medium">{log.user_name}</p>
                          <p className="text-xs text-muted">{log.user_role}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge className={badge.className}>{badge.label}</Badge>
                      </td>
                      <td className="px-4 py-3 text-muted">{log.resource_type}</td>
                      <td className="px-4 py-3 text-text max-w-xs truncate">{log.description}</td>
                      <td className="px-4 py-3 text-muted font-mono text-xs">{log.ip_address}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && !error && logs.length > 0 && (
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
