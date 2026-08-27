import { useState, useEffect, useCallback, type ReactNode } from 'react';
import {
  Trophy,
  BookOpen,
  HelpCircle,
  MessageSquare,
  FileText,
  Heart,
  Star,
  Eye,
  PenLine,
  Search,
  ClipboardList,
  Bot,
  AlertTriangle,
} from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Tabs } from '../../components/ui/Tabs';
import { Avatar } from '../../components/ui/Avatar';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { PageHeader } from '../../components/ui/PageHeader';
import { EmptyState } from '../../components/ui/EmptyState';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Textarea } from '../../components/ui/Textarea';
import {
  communityService,
  CATEGORY_OPTIONS,
  CATEGORY_BADGE_VARIANTS,
  type PostListItem,
  type PostDetail,
  type CommentItem,
} from '../../services/communityService';

// ---- Time formatting ----
function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return `${diffDay}天前`;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// ---- Category Icon Map ----
const CATEGORY_ICONS: Record<string, ReactNode> = {
  experience: <Trophy className="h-4 w-4 shrink-0" />,
  knowledge: <BookOpen className="h-4 w-4 shrink-0" />,
  question: <HelpCircle className="h-4 w-4 shrink-0" />,
  discussion: <MessageSquare className="h-4 w-4 shrink-0" />,
  script: <FileText className="h-4 w-4 shrink-0" />,
};

// ---- Post Card Component ----
function PostCard({
  post,
  onClick,
  onLike,
  onFavorite,
}: {
  post: PostListItem;
  onClick: () => void;
  onLike: () => void;
  onFavorite: () => void;
}) {
  return (
    <Card key={post.id} padding="md" hover onClick={onClick} className="cursor-pointer">
      <CardHeader>
        <div className="flex items-start gap-3">
          <Avatar name={post.author.name} size="sm" className="h-9 w-9" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-text/60">
                {CATEGORY_ICONS[post.category] ?? <MessageSquare className="h-4 w-4 shrink-0" />}
                {post.category_label}
              </span>
              {post.is_pinned && <Badge variant="error">置顶</Badge>}
              {post.is_recommended && <Badge variant="warning">推荐</Badge>}
            </div>
            <CardTitle className="text-sm mt-1 line-clamp-1">{post.title}</CardTitle>
            <div className="flex items-center gap-2 text-xs text-muted mt-1">
              <span className="font-medium text-text/70">{post.author.name}</span>
              <span>·</span>
              <span>{post.author.role === 'team_leader' ? '团队主管' : post.author.role === 'knowledge_admin' ? '知识管理' : post.author.role === 'compliance' ? '合规' : '代理人'}</span>
              <span>·</span>
              <span>{formatTime(post.created_at)}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardDescription className="line-clamp-2 ml-12 text-sm">
        {post.summary || ''}
      </CardDescription>
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border ml-12">
        <div className="flex gap-1.5 flex-wrap">
          {post.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="px-2 py-0.5 rounded text-xs bg-bg text-muted">
              {tag}
            </span>
          ))}
          {post.tags.length > 3 && (
            <span className="px-2 py-0.5 rounded text-xs bg-bg text-muted">
              +{post.tags.length - 3}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs text-muted shrink-0 ml-2">
          <span
            className={`inline-flex items-center gap-1 cursor-pointer hover:text-text transition-colors ${post.is_liked_by_me ? 'text-error' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onLike();
            }}
          >
            <Heart className={`h-[18px] w-[18px] ${post.is_liked_by_me ? 'fill-current' : ''}`} />
            {post.likes_count}
          </span>
          <span className="inline-flex items-center gap-1">
            <MessageSquare className="h-[18px] w-[18px]" />
            {post.comments_count}
          </span>
          <span className="inline-flex items-center gap-1">
            <Eye className="h-[18px] w-[18px]" />
            {post.views_count}
          </span>
          <span
            className={`cursor-pointer hover:text-text transition-colors ${post.is_favorited_by_me ? 'text-warning' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onFavorite();
            }}
          >
            <Star className={`h-[18px] w-[18px] ${post.is_favorited_by_me ? 'fill-current' : ''}`} />
          </span>
        </div>
      </div>
    </Card>
  );
}

// ---- Post Detail Modal ----
function PostDetailModal({
  postId,
  onClose,
}: {
  postId: string;
  onClose: () => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [commentText, setCommentText] = useState('');
  const [aiSummary, setAiSummary] = useState('');
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => {
    loadDetail();
  }, [postId]);

  async function loadDetail() {
    setLoading(true);
    try {
      const [detailRes, commentsRes] = await Promise.all([
        communityService.getPost(postId),
        communityService.listComments(postId),
      ]);
      if (detailRes) setPost(detailRes);
      if (commentsRes) setComments(commentsRes.items || []);
    } catch (err) {
      console.error('Failed to load post detail:', err);
    }
    setLoading(false);
  }

  async function handleLike() {
    if (!post) return;
    const result = await communityService.toggleLike(post.id);
    if (result && post) {
      setPost({ ...post, is_liked_by_me: result.is_liked, likes_count: result.likes_count });
    }
  }

  async function handleFavorite() {
    if (!post) return;
    const result = await communityService.toggleFavorite(post.id);
    if (result && post) {
      setPost({ ...post, is_favorited_by_me: result.is_favorited, favorites_count: result.favorites_count });
    }
  }

  async function handleSubmitComment() {
    if (!commentText.trim() || !post) return;
    setSubmitting(true);
    try {
      const result = await communityService.addComment(post.id, { content: commentText.trim() });
      if (result) {
        setComments((prev) => [
          {
            id: result.id,
            content: result.content,
            author: result.author,
            parent_comment_id: null,
            likes_count: 0,
            is_liked_by_me: false,
            replies: [],
            created_at: result.created_at,
          },
          ...prev,
        ]);
        setCommentText('');
        if (post) setPost({ ...post, comments_count: post.comments_count + 1 });
      }
    } catch (err) {
      console.error('Failed to submit comment:', err);
    }
    setSubmitting(false);
  }

  async function handleAiSummary() {
    if (!post) return;
    setIsGeneratingSummary(true);
    setAiSummary('');
    try {
      for await (const event of communityService.streamAiSummary(post.id)) {
        if (event.event === 'token' && event.data?.content) {
          setAiSummary((prev) => prev + event.data.content);
        } else if (event.event === 'summary_complete') {
          if (event.data?.summary) {
            setAiSummary(event.data.summary);
          }
          setIsGeneratingSummary(false);
          // Update post with AI summary
          if (post) setPost({ ...post, ai_summary: event.data.summary });
        } else if (event.event === 'error') {
          setIsGeneratingSummary(false);
        }
      }
    } catch (err) {
      console.error('Failed to generate AI summary:', err);
      setIsGeneratingSummary(false);
    }
  }

  if (loading) {
    return (
      <Modal open onClose={onClose} size="md">
        <LoadingSpinner text="加载中..." />
      </Modal>
    );
  }

  if (!post) return null;

  return (
    <Modal open onClose={onClose} title={post.title} size="lg">
      {/* Badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant={CATEGORY_BADGE_VARIANTS[post.category] || 'default'}>
          {CATEGORY_ICONS[post.category]}
          {post.category_label}
        </Badge>
        {post.is_pinned && <Badge variant="error">置顶</Badge>}
        {post.is_recommended && <Badge variant="warning">推荐</Badge>}
      </div>

      {/* Author meta */}
      <div className="flex items-center gap-2 text-xs text-muted mt-2">
        <Avatar name={post.author.name} size="sm" className="h-6 w-6" />
        <span className="font-medium text-text/70">{post.author.name}</span>
        <span>·</span>
        <span>{formatTime(post.created_at)}</span>
        <span>·</span>
        <span className="inline-flex items-center gap-1">
          <Eye className="h-4 w-4" />
          {post.views_count}
        </span>
      </div>

      {/* Content */}
      <div className="prose prose-sm max-w-none text-text/80 whitespace-pre-wrap leading-relaxed mt-4">
        {post.content}
      </div>

      {/* Tags + Actions */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex gap-1.5 flex-wrap">
          {post.tags.map((tag) => (
            <span key={tag} className="px-2 py-0.5 rounded text-xs bg-bg text-muted">
              #{tag}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <button
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              post.is_liked_by_me
                ? 'bg-error/10 text-error'
                : 'bg-bg text-muted hover:text-text'
            }`}
            onClick={handleLike}
          >
            <Heart className={`h-4 w-4 ${post.is_liked_by_me ? 'fill-current' : ''}`} />
            {post.likes_count}
          </button>
          <button
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              post.is_favorited_by_me
                ? 'bg-warning/10 text-warning'
                : 'bg-bg text-muted hover:text-text'
            }`}
            onClick={handleFavorite}
          >
            <Star className={`h-4 w-4 ${post.is_favorited_by_me ? 'fill-current' : ''}`} />
            {post.favorites_count || 0}
          </button>
        </div>
      </div>

      {/* AI Summary Section */}
      <div className="mt-4 border border-border rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-sm font-medium text-text">
            <Bot className="h-4 w-4 text-accent" />
            AI 摘要
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleAiSummary}
            disabled={isGeneratingSummary}
          >
            {isGeneratingSummary ? '生成中...' : post.ai_summary ? '重新生成' : '生成摘要'}
          </Button>
        </div>
        {(aiSummary || post.ai_summary) ? (
          <div className="text-sm text-text/70 leading-relaxed">
            {aiSummary || post.ai_summary}
          </div>
        ) : (
          <div className="text-sm text-muted">点击"生成摘要"，AI 将自动提炼本文核心内容</div>
        )}
        {(aiSummary || post.ai_summary) && (
          <div className="inline-flex items-center gap-1 text-xs text-muted mt-2">
            <AlertTriangle className="h-4 w-4" />
            AI 生成内容仅供参考
          </div>
        )}
      </div>

      {/* Comments Section */}
      <div className="mt-4 border-t border-border pt-4">
        <h3 className="flex items-center gap-1.5 text-sm font-semibold text-text mb-3">
          <MessageSquare className="h-4 w-4" />
          评论 ({comments.length})
        </h3>

        {/* Comment Input */}
        <div className="flex gap-2 mb-4 items-center">
          <div className="flex-1">
            <Input
              type="text"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmitComment()}
              placeholder="写下你的评论..."
              maxLength={500}
            />
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmitComment}
            disabled={!commentText.trim() || submitting}
          >
            发送
          </Button>
        </div>

        {/* Comment List */}
        <div className="space-y-3 max-h-80 overflow-y-auto">
          {comments.map((comment) => (
            <div key={comment.id}>
              <div className="flex items-start gap-2">
                <Avatar name={comment.author.name} size="sm" className="h-7 w-7" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-medium text-text/70">{comment.author.name}</span>
                    <span className="text-muted">{formatTime(comment.created_at)}</span>
                  </div>
                  <p className="text-sm text-text/80 mt-1">{comment.content}</p>
                  {/* Replies */}
                  {comment.replies && comment.replies.length > 0 && (
                    <div className="mt-2 ml-4 border-l-2 border-border pl-3 space-y-2">
                      {comment.replies.map((reply) => (
                        <div key={reply.id} className="flex items-start gap-2">
                          <Avatar name={reply.author.name} size="sm" className="h-5 w-5 text-[10px]" />
                          <div>
                            <div className="flex items-center gap-2 text-xs">
                              <span className="font-medium text-text/70">{reply.author.name}</span>
                              <span className="text-muted">{formatTime(reply.created_at)}</span>
                            </div>
                            <p className="text-sm text-text/80 mt-0.5">{reply.content}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {comments.length === 0 && (
            <div className="text-center text-sm text-muted py-4">暂无评论，来发表第一条吧</div>
          )}
        </div>
      </div>
    </Modal>
  );
}

// ---- Create Post Modal ----
function CreatePostModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [category, setCategory] = useState('discussion');
  const [tagsInput, setTagsInput] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!title.trim() || !content.trim()) return;
    setSubmitting(true);
    try {
      const tags = tagsInput
        .split(/[,，、]/)
        .map((t) => t.trim())
        .filter(Boolean)
        .slice(0, 5);
      await communityService.createPost({ title: title.trim(), content: content.trim(), category, tags });
      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to create post:', err);
    }
    setSubmitting(false);
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="发布帖子"
      size="lg"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            取消
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmit}
            disabled={!title.trim() || !content.trim() || submitting}
          >
            {submitting ? '发布中...' : '发布'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Input
          label="标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="输入帖子标题..."
          maxLength={200}
        />

        <div>
          <p className="text-sm font-medium text-text mb-1.5">分类</p>
          <div className="flex gap-2 flex-wrap">
            {CATEGORY_OPTIONS.filter((o) => o.value).map((opt) => (
              <button
                key={opt.value}
                onClick={() => setCategory(opt.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  category === opt.value
                    ? 'bg-accent text-white'
                    : 'bg-bg text-muted border border-border hover:text-text'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <Textarea
            label="内容"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="分享你的经验、知识或提问..."
            rows={8}
            className="resize-none"
            maxLength={5000}
          />
          <div className="text-xs text-muted mt-1">{content.length}/5000</div>
        </div>

        <Input
          label="标签（可选，逗号分隔，最多5个）"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder="例如：实战技巧, 新人入门, 异议处理"
        />
      </div>
    </Modal>
  );
}

// ---- Main Community Page ----
export function CommunityPage() {
  const user = useAuthStore((s) => s.user);
  const [activeTab, setActiveTab] = useState<'posts' | 'favorites'>('posts');
  const [posts, setPosts] = useState<PostListItem[]>([]);
  const [pagination, setPagination] = useState({ page: 1, total: 0, total_pages: 0 });
  const [loading, setLoading] = useState(true);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState('');
  const [sortBy, setSortBy] = useState('created_at');

  const loadPosts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await communityService.listPosts({
        keyword: keyword || undefined,
        category: category || undefined,
        sort_by: sortBy,
        page: pagination.page,
        page_size: 20,
      });
      setPosts(res.items || []);
      setPagination((prev) => ({
        ...prev,
        total: res.pagination?.total || 0,
        total_pages: res.pagination?.total_pages || 0,
      }));
    } catch (err) {
      console.error('Failed to load posts:', err);
    }
    setLoading(false);
  }, [keyword, category, sortBy, pagination.page]);

  const loadFavorites = useCallback(async () => {
    setLoading(true);
    try {
      const res = await communityService.myFavorites({
        page: pagination.page,
        page_size: 20,
      });
      setPosts(res.items || []);
      setPagination((prev) => ({
        ...prev,
        total: res.pagination?.total || 0,
        total_pages: res.pagination?.total_pages || 0,
      }));
    } catch (err) {
      console.error('Failed to load favorites:', err);
    }
    setLoading(false);
  }, [pagination.page]);

  useEffect(() => {
    if (activeTab === 'posts') loadPosts();
    else loadFavorites();
  }, [activeTab, loadPosts, loadFavorites]);

  // Reset page when filters change
  useEffect(() => {
    setPagination((prev) => ({ ...prev, page: 1 }));
  }, [keyword, category, sortBy]);

  async function handleToggleLike(postId: string) {
    const result = await communityService.toggleLike(postId);
    if (result) {
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId
            ? { ...p, is_liked_by_me: result.is_liked, likes_count: result.likes_count }
            : p,
        ),
      );
    }
  }

  async function handleToggleFavorite(postId: string) {
    const result = await communityService.toggleFavorite(postId);
    if (result) {
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId
            ? { ...p, is_favorited_by_me: result.is_favorited, favorites_count: result.favorites_count }
            : p,
        ),
      );
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <PageHeader
        title="AI社区"
        description={`${user?.name || '用户'}，与同事分享经验，AI精选优秀案例和销售心得`}
        actions={
          <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
            <PenLine className="h-4 w-4" />
            发布帖子
          </Button>
        }
      />

      {/* Tabs */}
      <Tabs
        variant="pill"
        active={activeTab}
        onChange={(key) => setActiveTab(key as 'posts' | 'favorites')}
        items={[
          {
            key: 'posts',
            label: (
              <span className="inline-flex items-center gap-1.5">
                <ClipboardList className="h-4 w-4" />
                帖子列表
              </span>
            ),
          },
          {
            key: 'favorites',
            label: (
              <span className="inline-flex items-center gap-1.5">
                <Star className="h-4 w-4" />
                我的收藏
              </span>
            ),
          },
        ]}
      />

      {/* Filters (only for posts tab) */}
      {activeTab === 'posts' && (
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              icon={<Search className="h-4 w-4" />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="搜索帖子..."
            />
          </div>
          <div className="sm:w-44">
            <Select
              aria-label="按分类筛选"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </div>
          <div className="sm:w-40">
            <Select
              aria-label="排序方式"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="created_at">最新发布</option>
              <option value="likes_count">最多点赞</option>
              <option value="comments_count">最多评论</option>
              <option value="views_count">最多浏览</option>
            </Select>
          </div>
        </div>
      )}

      {/* Posts */}
      <div className="space-y-3">
        {loading ? (
          <LoadingSpinner text="加载中..." />
        ) : posts.length === 0 ? (
          <EmptyState
            icon={
              activeTab === 'favorites' ? (
                <Star className="h-5 w-5 text-muted" />
              ) : (
                <MessageSquare className="h-5 w-5 text-muted" />
              )
            }
            title={activeTab === 'favorites' ? '暂无收藏的帖子' : '暂无帖子'}
          />
        ) : (
          posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onClick={() => setSelectedPostId(post.id)}
              onLike={() => handleToggleLike(post.id)}
              onFavorite={() => handleToggleFavorite(post.id)}
            />
          ))
        )}
      </div>

      {/* Pagination */}
      {pagination.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 py-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPagination((prev) => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
            disabled={pagination.page <= 1}
          >
            ← 上一页
          </Button>
          <span className="text-xs text-muted">
            {pagination.page} / {pagination.total_pages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setPagination((prev) => ({
                ...prev,
                page: Math.min(prev.total_pages, prev.page + 1),
              }))
            }
            disabled={pagination.page >= pagination.total_pages}
          >
            下一页 →
          </Button>
        </div>
      )}

      {/* Post Detail Modal */}
      {selectedPostId && (
        <PostDetailModal
          postId={selectedPostId}
          onClose={() => setSelectedPostId(null)}
        />
      )}

      {/* Create Post Modal */}
      {showCreate && (
        <CreatePostModal
          onClose={() => setShowCreate(false)}
          onSuccess={() => {
            if (activeTab === 'posts') loadPosts();
          }}
        />
      )}
    </div>
  );
}
