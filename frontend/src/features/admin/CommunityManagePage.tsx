import { useCallback, useEffect, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { useToast } from '../../hooks/useToast';
import { adminCommunityApi, type AdminPost } from '../../services/adminService';
import { cn } from '../../utils/cn';

// ----------- Constants -----------

const STATUS_VARIANT_MAP: Record<string, 'success' | 'warning' | 'error'> = {
  published: 'success',
  pending_review: 'warning',
  reported: 'error',
};

const STATUS_LABEL_MAP: Record<string, string> = {
  published: '已发布',
  pending_review: '待审核',
  reported: '已举报',
};

const STATUS_FILTERS = [
  { key: '', label: '全部状态' },
  { key: 'published', label: '已发布' },
  { key: 'reported', label: '已举报' },
  { key: 'pending_review', label: '待审核' },
];

const CATEGORY_FILTERS = [
  { key: '', label: '全部分类' },
  { key: 'knowledge', label: '知识分享' },
  { key: 'experience', label: '经验交流' },
  { key: 'question', label: '问题求助' },
  { key: 'product', label: '产品讨论' },
];

// ----------- Icons (inline SVG) -----------

function ThumbtackIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      className={cn('w-4 h-4', filled ? 'text-accent' : 'text-muted')}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 17v5" />
      <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1h0a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h0a1 1 0 0 1 1 1z" />
    </svg>
  );
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      className={cn('w-4 h-4', filled ? 'text-warning' : 'text-muted')}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

// ----------- Page -----------

export function CommunityManagePage() {
  const { toast } = useToast();

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Data
  const [posts, setPosts] = useState<AdminPost[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminCommunityApi.listPosts({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        page,
        page_size: pageSize,
      });
      const body = res.data;
      setPosts(body.data);
      setTotal(body.pagination.total);
      setTotalPages(body.pagination.total_pages);
    } catch {
      setError('加载帖子列表失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, categoryFilter, page]);

  useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [statusFilter, categoryFilter]);

  const handleTogglePin = async (post: AdminPost) => {
    setActionLoading(post.id);
    try {
      await adminCommunityApi.togglePin(post.id, !post.is_pinned);
      toast({
        title: post.is_pinned ? `已取消置顶「${post.title}」` : `已置顶「${post.title}」`,
        variant: 'success',
      });
      fetchPosts();
    } catch {
      toast({ title: '操作失败，请重试', variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleRecommend = async (post: AdminPost) => {
    setActionLoading(post.id);
    try {
      await adminCommunityApi.toggleRecommend(post.id, !post.is_recommended);
      toast({
        title: post.is_recommended ? `已取消推荐「${post.title}」` : `已推荐「${post.title}」`,
        variant: 'success',
      });
      fetchPosts();
    } catch {
      toast({ title: '操作失败，请重试', variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (post: AdminPost) => {
    if (!window.confirm(`确定要删除帖子「${post.title}」吗？此操作不可恢复。`)) return;
    setActionLoading(post.id);
    try {
      await adminCommunityApi.deletePost(post.id);
      toast({ title: '已删除', variant: 'success' });
      fetchPosts();
    } catch {
      toast({ title: '删除失败，请重试', variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-text">社区管理</h1>
          <Badge variant="warning">演示模式</Badge>
        </div>
        <p className="text-muted text-sm mt-1">
          共 {total} 篇帖子 · 管理社区内容与运营
        </p>
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
          </div>
        </div>
      </Card>

      {/* Posts Table */}
      <Card padding="none">
        {loading ? (
          <div className="py-16">
            <LoadingSpinner text="加载帖子列表..." />
          </div>
        ) : error ? (
          <div className="py-16 text-center">
            <p className="text-error text-sm mb-3">{error}</p>
            <Button variant="secondary" size="sm" onClick={fetchPosts}>
              重新加载
            </Button>
          </div>
        ) : posts.length === 0 ? (
          <div className="py-16 text-center text-muted text-sm">
            未找到匹配的帖子
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 font-medium text-muted">标题</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">作者</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">分类</th>
                  <th className="text-left px-4 py-3 font-medium text-muted">状态</th>
                  <th className="text-right px-4 py-3 font-medium text-muted">浏览</th>
                  <th className="text-right px-4 py-3 font-medium text-muted">点赞</th>
                  <th className="text-right px-4 py-3 font-medium text-muted">评论</th>
                  <th className="text-center px-4 py-3 font-medium text-muted">置顶</th>
                  <th className="text-center px-4 py-3 font-medium text-muted">推荐</th>
                  <th className="text-right px-4 py-3 font-medium text-muted">操作</th>
                </tr>
              </thead>
              <tbody>
                {posts.map((post) => (
                  <tr
                    key={post.id}
                    className="border-b border-border last:border-b-0 hover:bg-bg/50 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-text max-w-[200px] truncate">
                      {post.title}
                    </td>
                    <td className="px-4 py-3 text-muted">{post.author_name}</td>
                    <td className="px-4 py-3">
                      <Badge variant="default">{post.category_label}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_VARIANT_MAP[post.status] || 'default'}>
                        {STATUS_LABEL_MAP[post.status] || post.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-muted">{post.views_count}</td>
                    <td className="px-4 py-3 text-right text-muted">{post.likes_count}</td>
                    <td className="px-4 py-3 text-right text-muted">{post.comments_count}</td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleTogglePin(post)}
                        disabled={actionLoading === post.id}
                        className="inline-flex cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        title={post.is_pinned ? '取消置顶' : '置顶'}
                      >
                        <ThumbtackIcon filled={post.is_pinned} />
                      </button>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggleRecommend(post)}
                        disabled={actionLoading === post.id}
                        className="inline-flex cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        title={post.is_recommended ? '取消推荐' : '推荐'}
                      >
                        <StarIcon filled={post.is_recommended} />
                      </button>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        loading={actionLoading === post.id}
                        onClick={() => handleDelete(post)}
                        className="text-error hover:text-error"
                      >
                        删除
                      </Button>
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
