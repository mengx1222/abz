import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  communityService,
  CATEGORY_OPTIONS,
  CATEGORY_BADGE_VARIANTS,
  type PostListItem,
  type PostDetail,
  type CommentItem,
  type PaginatedData,
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
const CATEGORY_ICONS: Record<string, string> = {
  experience: '🏆',
  knowledge: '📚',
  question: '❓',
  discussion: '💬',
  script: '📝',
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
          <div className="w-9 h-9 rounded-full bg-accent/10 text-accent flex items-center justify-center text-sm font-bold shrink-0">
            {post.author.name[0]}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-text/60">
                {CATEGORY_ICONS[post.category] || '💬'} {post.category_label}
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
        {post.summary || post.content?.slice(0, 100) || ''}
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
            className={`cursor-pointer hover:text-text transition-colors ${post.is_liked_by_me ? 'text-red-500' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onLike();
            }}
          >
            {post.is_liked_by_me ? '❤️' : '🤍'} {post.likes_count}
          </span>
          <span>💬 {post.comments_count}</span>
          <span>👁 {post.views_count}</span>
          <span
            className={`cursor-pointer hover:text-text transition-colors ${post.is_favorited_by_me ? 'text-yellow-500' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onFavorite();
            }}
          >
            {post.is_favorited_by_me ? '⭐' : '☆'}
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
  const user = useAuthStore((s) => s.user);

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
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={onClose}>
        <div className="bg-card rounded-xl p-8 max-w-2xl w-full mx-4">
          <div className="animate-pulse text-center text-muted">加载中...</div>
        </div>
      </div>
    );
  }

  if (!post) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto py-8" onClick={onClose}>
      <div className="bg-card rounded-xl max-w-3xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 pb-0">
          <div className="flex items-center gap-2">
            <Badge variant={CATEGORY_BADGE_VARIANTS[post.category] || 'default'}>
              {CATEGORY_ICONS[post.category]} {post.category_label}
            </Badge>
            {post.is_pinned && <Badge variant="error">置顶</Badge>}
            {post.is_recommended && <Badge variant="warning">推荐</Badge>}
          </div>
          <button onClick={onClose} className="text-muted hover:text-text text-xl">✕</button>
        </div>

        {/* Title */}
        <div className="px-6 pt-3">
          <h2 className="text-lg font-bold text-text">{post.title}</h2>
          <div className="flex items-center gap-2 text-xs text-muted mt-2">
            <div className="w-6 h-6 rounded-full bg-accent/10 text-accent flex items-center justify-center text-xs font-bold">
              {post.author.name[0]}
            </div>
            <span className="font-medium text-text/70">{post.author.name}</span>
            <span>·</span>
            <span>{formatTime(post.created_at)}</span>
            <span>·</span>
            <span>👁 {post.views_count}</span>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <div className="prose prose-sm max-w-none text-text/80 whitespace-pre-wrap leading-relaxed">
            {post.content}
          </div>
        </div>

        {/* Tags + Actions */}
        <div className="px-6 pb-4 flex items-center justify-between">
          <div className="flex gap-1.5 flex-wrap">
            {post.tags.map((tag) => (
              <span key={tag} className="px-2 py-0.5 rounded text-xs bg-bg text-muted">
                #{tag}
              </span>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <button
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                post.is_liked_by_me
                  ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400'
                  : 'bg-bg text-muted hover:text-text'
              }`}
              onClick={handleLike}
            >
              {post.is_liked_by_me ? '❤️' : '🤍'} {post.likes_count}
            </button>
            <button
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                post.is_favorited_by_me
                  ? 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/20 dark:text-yellow-400'
                  : 'bg-bg text-muted hover:text-text'
              }`}
              onClick={handleFavorite}
            >
              {post.is_favorited_by_me ? '⭐' : '☆'} {post.favorites_count || 0}
            </button>
          </div>
        </div>

        {/* AI Summary Section */}
        <div className="px-6 pb-4">
          <div className="border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm font-medium text-text">
                🤖 AI 摘要
              </div>
              <button
                className="px-3 py-1 rounded-md text-xs bg-accent/10 text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
                onClick={handleAiSummary}
                disabled={isGeneratingSummary}
              >
                {isGeneratingSummary ? '生成中...' : post.ai_summary ? '重新生成' : '生成摘要'}
              </button>
            </div>
            {(aiSummary || post.ai_summary) ? (
              <div className="text-sm text-text/70 leading-relaxed">
                {aiSummary || post.ai_summary}
              </div>
            ) : (
              <div className="text-sm text-muted">点击"生成摘要"，AI 将自动提炼本文核心内容</div>
            )}
            {(aiSummary || post.ai_summary) && (
              <div className="text-xs text-muted mt-2">⚠️ AI 生成内容仅供参考</div>
            )}
          </div>
        </div>

        {/* Comments Section */}
        <div className="px-6 pb-6">
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-semibold text-text mb-3">
              💬 评论 ({comments.length})
            </h3>

            {/* Comment Input */}
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmitComment()}
                placeholder="写下你的评论..."
                className="flex-1 px-3 py-2 rounded-lg bg-bg border border-border text-sm text-text placeholder-muted focus:outline-none focus:border-accent"
                maxLength={500}
              />
              <button
                onClick={handleSubmitComment}
                disabled={!commentText.trim() || submitting}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 disabled:opacity-50 transition-colors"
              >
                发送
              </button>
            </div>

            {/* Comment List */}
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {comments.map((comment) => (
                <div key={comment.id}>
                  <div className="flex items-start gap-2">
                    <div className="w-7 h-7 rounded-full bg-accent/10 text-accent flex items-center justify-center text-xs font-bold shrink-0">
                      {comment.author.name[0]}
                    </div>
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
                              <div className="w-5 h-5 rounded-full bg-accent/10 text-accent flex items-center justify-center text-[10px] font-bold shrink-0">
                                {reply.author.name[0]}
                              </div>
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
        </div>
      </div>
    </div>
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
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="bg-card rounded-xl max-w-xl w-full mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-text">发布帖子</h2>
          <button onClick={onClose} className="text-muted hover:text-text text-xl">✕</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text mb-1">标题</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="输入帖子标题..."
              className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-sm text-text placeholder-muted focus:outline-none focus:border-accent"
              maxLength={200}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text mb-1">分类</label>
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
            <label className="block text-sm font-medium text-text mb-1">内容</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="分享你的经验、知识或提问..."
              rows={8}
              className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-sm text-text placeholder-muted focus:outline-none focus:border-accent resize-none"
              maxLength={5000}
            />
            <div className="text-xs text-muted mt-1">{content.length}/5000</div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text mb-1">标签（可选，逗号分隔，最多5个）</label>
            <input
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="例如：实战技巧, 新人入门, 异议处理"
              className="w-full px-3 py-2 rounded-lg bg-bg border border-border text-sm text-text placeholder-muted focus:outline-none focus:border-accent"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
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
        </div>
      </div>
    </div>
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
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">AI社区</h1>
          </div>
          <p className="text-muted text-sm mt-1">
            {user?.name || '用户'}，与同事分享经验，AI精选优秀案例和销售心得
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
          + 发布帖子
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-bg rounded-lg">
        <button
          onClick={() => setActiveTab('posts')}
          className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'posts'
              ? 'bg-card text-text shadow-sm'
              : 'text-muted hover:text-text'
          }`}
        >
          📋 帖子列表
        </button>
        <button
          onClick={() => setActiveTab('favorites')}
          className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'favorites'
              ? 'bg-card text-text shadow-sm'
              : 'text-muted hover:text-text'
          }`}
        >
          ⭐ 我的收藏
        </button>
      </div>

      {/* Filters (only for posts tab) */}
      {activeTab === 'posts' && (
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索帖子..."
            className="flex-1 px-3 py-2 rounded-lg bg-bg border border-border text-sm text-text placeholder-muted focus:outline-none focus:border-accent"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-3 py-2 rounded-lg bg-bg border border-border text-sm text-text focus:outline-none focus:border-accent"
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 rounded-lg bg-bg border border-border text-sm text-text focus:outline-none focus:border-accent"
          >
            <option value="created_at">最新发布</option>
            <option value="likes_count">最多点赞</option>
            <option value="comments_count">最多评论</option>
            <option value="views_count">最多浏览</option>
          </select>
        </div>
      )}

      {/* Posts */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12 text-muted">加载中...</div>
        ) : posts.length === 0 ? (
          <div className="text-center py-12 text-muted">
            {activeTab === 'favorites' ? '暂无收藏的帖子' : '暂无帖子'}
          </div>
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
          <button
            onClick={() => setPagination((prev) => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
            disabled={pagination.page <= 1}
            className="px-3 py-1.5 rounded-lg text-xs bg-bg text-muted hover:text-text disabled:opacity-50 transition-colors"
          >
            ← 上一页
          </button>
          <span className="text-xs text-muted">
            {pagination.page} / {pagination.total_pages}
          </span>
          <button
            onClick={() =>
              setPagination((prev) => ({
                ...prev,
                page: Math.min(prev.total_pages, prev.page + 1),
              }))
            }
            disabled={pagination.page >= pagination.total_pages}
            className="px-3 py-1.5 rounded-lg text-xs bg-bg text-muted hover:text-text disabled:opacity-50 transition-colors"
          >
            下一页 →
          </button>
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
