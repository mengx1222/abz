import api from './api';

// ---- Types ----

export interface AuthorBrief {
  id: string;
  name: string;
  avatar?: string | null;
  role: string;
  organization?: string | null;
}

export interface PostListItem {
  id: string;
  title: string;
  author: AuthorBrief;
  category: string;
  category_label: string;
  summary?: string | null;
  tags: string[];
  views_count: number;
  likes_count: number;
  comments_count: number;
  is_pinned: boolean;
  is_recommended: boolean;
  is_liked_by_me: boolean;
  is_favorited_by_me: boolean;
  created_at: string;
}

export interface PostDetail extends PostListItem {
  content: string;
  ai_summary?: string | null;
  updated_at?: string | null;
}

export interface CommentAuthor {
  id: string;
  name: string;
  avatar?: string | null;
}

export interface CommentItem {
  id: string;
  content: string;
  author: CommentAuthor;
  parent_comment_id: string | null;
  likes_count: number;
  is_liked_by_me: boolean;
  replies: CommentItem[];
  created_at: string;
}

export interface PaginatedData<T> {
  items: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  request_id?: string;
}

// ---- Community Service ----

export const communityService = {
  // 帖子列表
  async listPosts(params: {
    keyword?: string;
    category?: string;
    tags?: string;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedData<PostListItem>> {
    const res = await api.get<ApiResponse<PaginatedData<PostListItem>>>('/community/posts', { params });
    return res.data.data;
  },

  // 帖子详情
  async getPost(postId: string): Promise<PostDetail | null> {
    const res = await api.get<ApiResponse<PostDetail | null>>(`/community/posts/${postId}`);
    return res.data.data;
  },

  // 发布帖子
  async createPost(data: {
    title: string;
    content: string;
    category: string;
    tags?: string[];
  }): Promise<{ id: string; title: string; status: string; created_at: string }> {
    const res = await api.post<ApiResponse<{ id: string; title: string; status: string; created_at: string }>>(
      '/community/posts',
      data,
    );
    return res.data.data;
  },

  // 更新帖子
  async updatePost(postId: string, data: {
    title?: string;
    content?: string;
    category?: string;
    tags?: string[];
  }): Promise<{ id: string; status: string; updated_at: string } | null> {
    const res = await api.put<ApiResponse<{ id: string; status: string; updated_at: string } | null>>(
      `/community/posts/${postId}`,
      data,
    );
    return res.data.data;
  },

  // 删除帖子
  async deletePost(postId: string): Promise<boolean> {
    const res = await api.delete<ApiResponse<{ deleted: boolean } | null>>(`/community/posts/${postId}`);
    return !!res.data.data;
  },

  // 点赞/取消
  async toggleLike(postId: string): Promise<{ is_liked: boolean; likes_count: number } | null> {
    const res = await api.post<ApiResponse<{ is_liked: boolean; likes_count: number } | null>>(
      `/community/posts/${postId}/like`,
    );
    return res.data.data;
  },

  // 收藏/取消
  async toggleFavorite(postId: string): Promise<{ is_favorited: boolean; favorites_count: number } | null> {
    const res = await api.post<ApiResponse<{ is_favorited: boolean; favorites_count: number } | null>>(
      `/community/posts/${postId}/favorite`,
    );
    return res.data.data;
  },

  // 评论列表
  async listComments(postId: string, params: { page?: number; page_size?: number } = {}): Promise<PaginatedData<CommentItem>> {
    const res = await api.get<ApiResponse<PaginatedData<CommentItem>>>(
      `/community/posts/${postId}/comments`,
      { params },
    );
    return res.data.data;
  },

  // 发表评论
  async addComment(
    postId: string,
    data: { content: string; parent_comment_id?: string | null },
  ): Promise<{ id: string; content: string; author: CommentAuthor; created_at: string } | null> {
    const res = await api.post<ApiResponse<{ id: string; content: string; author: CommentAuthor; created_at: string } | null>>(
      `/community/posts/${postId}/comments`,
      data,
    );
    return res.data.data;
  },

  // 我的收藏
  async myFavorites(params: { page?: number; page_size?: number } = {}): Promise<PaginatedData<PostListItem>> {
    const res = await api.get<ApiResponse<PaginatedData<PostListItem>>>('/community/favorites', { params });
    return res.data.data;
  },

  // AI 摘要 SSE
  async *streamAiSummary(postId: string): AsyncGenerator<{ event: string; data: any }, void> {
    const token = localStorage.getItem('auth_token');
    const response = await fetch(`/api/v1/community/posts/${postId}/ai-summary`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'text/event-stream',
      },
    });

    if (!response.ok || !response.body) {
      throw new Error('Failed to fetch AI summary');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const json = JSON.parse(line.slice(6));
            yield json;
          } catch {
            // skip malformed JSON
          }
        }
      }
    }
  },
};

// Category options for filters
export const CATEGORY_OPTIONS = [
  { value: '', label: '全部分类' },
  { value: 'experience', label: '实战经验' },
  { value: 'knowledge', label: '知识分享' },
  { value: 'question', label: '求助提问' },
  { value: 'discussion', label: '讨论' },
  { value: 'script', label: '优秀话术' },
] as const;

export const CATEGORY_BADGE_VARIANTS: Record<string, 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info'> = {
  experience: 'success',
  knowledge: 'primary',
  question: 'warning',
  discussion: 'default',
  script: 'info',
};
