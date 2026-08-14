import { useCallback, useEffect, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { useToast } from '../../hooks/useToast';
import { adminUserApi, type AdminUser } from '../../services/adminService';

// ----------- Constants -----------

const ROLE_VARIANT_MAP: Record<string, 'default' | 'warning' | 'success' | 'error'> = {
  admin: 'error',
  manager: 'warning',
  agent: 'success',
  trainee: 'default',
};

const STATUS_OPTIONS = [
  { key: '', label: '全部状态' },
  { key: 'active', label: '已启用' },
  { key: 'disabled', label: '已禁用' },
];

const ROLE_OPTIONS = [
  { key: '', label: '全部角色' },
  { key: 'admin', label: '管理员' },
  { key: 'manager', label: '主管' },
  { key: 'agent', label: '代理人' },
  { key: 'trainee', label: '实习生' },
];

// ----------- Helpers -----------

function formatDateTime(dateStr?: string): string {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ----------- Page -----------

export function UsersPage() {
  const { toast } = useToast();

  // Filters
  const [keyword, setKeyword] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Data
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Actions
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminUserApi.list({
        keyword: keyword || undefined,
        role: roleFilter || undefined,
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      });
      const body = res.data;
      setUsers(body.data);
      setTotal(body.pagination.total);
      setTotalPages(body.pagination.total_pages);
    } catch {
      setError('加载用户列表失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [keyword, roleFilter, statusFilter, page]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [keyword, roleFilter, statusFilter]);

  const handleToggleStatus = async (user: AdminUser) => {
    setActionLoading(user.id);
    try {
      if (user.status === 'active') {
        await adminUserApi.disable(user.id, '管理员操作');
        toast({ title: `已禁用用户「${user.name}」`, variant: 'success' });
      } else {
        await adminUserApi.enable(user.id);
        toast({ title: `已启用用户「${user.name}」`, variant: 'success' });
      }
      fetchUsers();
    } catch {
      toast({ title: '操作失败，请重试', variant: 'error' });
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
            <h1 className="text-2xl font-bold text-text">用户管理</h1>
            <Badge variant="warning">演示模式</Badge>
          </div>
          <p className="text-muted text-sm mt-1">
            共 {total} 位用户 · 管理系统用户账号与权限
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => toast({ title: '演示模式下暂不支持创建用户', variant: 'warning' })}
        >
          + 创建用户
        </Button>
      </div>

      {/* Search & Filters */}
      <Card padding="md">
        <div className="flex flex-col gap-3">
          <Input
            placeholder="搜索姓名或手机号..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className="sm:w-64"
          />
          <div className="flex flex-wrap items-center gap-2">
            {/* Role filter */}
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="h-8 rounded-lg border border-border bg-white px-2 text-xs text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              {ROLE_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>

            <span className="text-border mx-1">|</span>

            {/* Status filter */}
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setStatusFilter(opt.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  statusFilter === opt.key
                    ? 'bg-accent text-white'
                    : 'bg-bg text-muted hover:text-text'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* User Table */}
      <Card padding="none">
        {loading ? (
          <div className="py-16">
            <LoadingSpinner text="加载用户列表..." />
          </div>
        ) : error ? (
          <div className="py-16 text-center">
            <p className="text-error text-sm mb-3">{error}</p>
            <Button variant="secondary" size="sm" onClick={fetchUsers}>
              重新加载
            </Button>
          </div>
        ) : users.length === 0 ? (
          <div className="py-16 text-center text-muted text-sm">
            未找到匹配的用户
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 font-medium text-muted">姓名</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">手机号</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">角色</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">所属机构</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">状态</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">最后登录</th>
                  <th className="text-right px-4 py-3 font-medium text-muted">操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-border last:border-b-0 hover:bg-bg/50 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-text">{user.name}</td>
                    <td className="px-4 py-3 text-muted">{user.phone}</td>
                    <td className="px-4 py-3">
                      <Badge variant={ROLE_VARIANT_MAP[user.role_code] || 'default'}>
                        {user.role_name}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-text">{user.organization_name}</td>
                    <td className="px-4 py-3">
                      <Badge variant={user.status === 'active' ? 'success' : 'error'}>
                        {user.status === 'active' ? '已启用' : '已禁用'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-muted">{formatDateTime(user.last_login_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
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
                          loading={actionLoading === user.id}
                          onClick={() => handleToggleStatus(user)}
                          className={
                            user.status === 'active'
                              ? 'text-error hover:text-error'
                              : 'text-success hover:text-success'
                          }
                        >
                          {user.status === 'active' ? '禁用' : '启用'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

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
    </div>
  );
}
