import api from './api';

// ==================== Types ====================

export interface AdminUser {
  id: string;
  phone: string;
  name: string;
  avatar_url?: string;
  role_code: string;
  role_name: string;
  organization_name: string;
  team_name?: string;
  status: string;
  last_login_at?: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string;
  user_name: string;
  user_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  description: string;
  ip_address: string;
  created_at: string;
}

export interface OverviewData {
  period: string;
  user_stats: { total_users: number; active_users: number; new_users: number; active_rate: number };
  customer_stats: { total_customers: number; new_customers: number; high_intent: number; conversion_rate: number };
  ai_stats: { total_interactions: number; satisfaction_rate: number; avg_response_time_ms: number };
  training_stats: { total_sessions: number; avg_score: number; completion_rate: number };
  community_stats: { total_posts: number; total_comments: number; active_contributors: number };
}

export interface AiUsageData {
  period: string;
  total_calls: number;
  feature_breakdown: { feature: string; count: number; percentage: number; label?: string }[];
  top_users: { user_id: string; name: string; usage_count: number }[];
  error_rate: number;
  avg_latency_ms: number;
  token_usage: { total_input_tokens: number; total_output_tokens: number; total_tokens: number };
}

export interface TrainingAnalytics {
  period: string;
  total_sessions: number;
  avg_score: number;
  completion_rate: number;
  scenario_popularity: { scenario: string; count: number }[];
  score_distribution: { range: string; count: number }[];
}

export interface CommunityAnalytics {
  period: string;
  total_posts: number;
  total_comments: number;
  active_contributors: number;
  category_distribution: { category: string; count: number; percentage: number }[];
  top_posts: { title: string; views: number; likes: number }[];
}

export interface ComplianceRule {
  id: string;
  name: string;
  description: string;
  category: string;
  severity: string;
  severity_label: string;
  keywords: string[];
  patterns: string[];
  is_active: boolean;
  created_at?: string;
}

export interface ComplianceReview {
  id: string;
  type: string;
  type_label: string;
  title: string;
  content_preview: string;
  author_name: string;
  severity: string;
  status: string;
  priority: string;
  created_at?: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

export interface AdminPost {
  id: string;
  title: string;
  author_name: string;
  category: string;
  category_label: string;
  status: string;
  views_count: number;
  likes_count: number;
  comments_count: number;
  is_pinned: boolean;
  is_recommended: boolean;
  created_at?: string;
}

export interface AdminScript {
  id: string;
  title: string;
  style: string;
  style_label: string;
  product_type: string;
  content_preview: string;
  author_name: string;
  status: string;
  compliance_status: string;
  usage_count: number;
  favorite_count: number;
  created_at?: string;
}

export interface AdminScenario {
  id: string;
  title: string;
  description: string;
  category: string;
  difficulty: string;
  status: string;
  duration_minutes: number;
  usage_count: number;
  avg_score: number;
  tags: string[];
  created_at?: string;
}

export interface SystemSettings {
  ai: Record<string, unknown>;
  rag: Record<string, unknown>;
  compliance: Record<string, unknown>;
  notification: Record<string, unknown>;
  community: Record<string, unknown>;
}

interface PaginatedData<T> {
  success: boolean;
  data: T[];
  pagination: { page: number; page_size: number; total: number; total_pages: number };
}

interface SuccessData<T> {
  success: boolean;
  data: T;
  message?: string;
}

// ==================== API Methods ====================

// 用户管理
export const adminUserApi = {
  list: (params?: { keyword?: string; role?: string; status?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedData<AdminUser>>('/admin/users', { params }),

  create: (data: { name: string; phone: string; role_code: string; organization_id: string; initial_password: string }) =>
    api.post<SuccessData<AdminUser>>('/admin/users', data),

  update: (userId: string, data: Partial<{ name: string; role_code: string }>) =>
    api.put<SuccessData<AdminUser>>(`/admin/users/${userId}`, data),

  disable: (userId: string, reason: string) =>
    api.post<SuccessData<{ id: string; status: string }>>(`/admin/users/${userId}/disable`, { reason }),

  enable: (userId: string) =>
    api.post<SuccessData<{ id: string; status: string }>>(`/admin/users/${userId}/enable`),
};

// 审计日志
export const auditLogApi = {
  list: (params?: { user_id?: string; action?: string; resource_type?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedData<AuditLog>>('/admin/audit-logs', { params }),
};

// 数据看板
export const analyticsApi = {
  overview: (period?: string) =>
    api.get<SuccessData<OverviewData>>('/admin/analytics/overview', { params: { period } }),

  aiUsage: (period?: string) =>
    api.get<SuccessData<AiUsageData>>('/admin/analytics/ai-usage', { params: { period } }),

  training: (period?: string) =>
    api.get<SuccessData<TrainingAnalytics>>('/admin/analytics/training', { params: { period } }),

  community: (period?: string) =>
    api.get<SuccessData<CommunityAnalytics>>('/admin/analytics/community', { params: { period } }),
};

// 合规中心
export const complianceApi = {
  listRules: () =>
    api.get<SuccessData<ComplianceRule[]>>('/admin/compliance/rules'),

  createRule: (data: Partial<ComplianceRule>) =>
    api.post<SuccessData<ComplianceRule>>('/admin/compliance/rules', data),

  updateRule: (ruleId: string, data: Partial<ComplianceRule>) =>
    api.put<SuccessData<ComplianceRule>>(`/admin/compliance/rules/${ruleId}`, data),

  listReviews: (params?: { status?: string; type?: string; priority?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedData<ComplianceReview>>('/admin/compliance/reviews', { params }),

  processReview: (reviewId: string, action: string, comment: string) =>
    api.post<SuccessData<ComplianceReview>>(`/admin/compliance/reviews/${reviewId}/process`, { action, comment }),
};

// 社区管理
export const adminCommunityApi = {
  listPosts: (params?: { status?: string; category?: string; keyword?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedData<AdminPost>>('/admin/community/posts', { params }),

  togglePin: (postId: string, is_pinned: boolean) =>
    api.post<SuccessData<{ id: string; is_pinned: boolean }>>(`/admin/community/posts/${postId}/pin`, { is_pinned }),

  toggleRecommend: (postId: string, is_recommended: boolean) =>
    api.post<SuccessData<{ id: string; is_recommended: boolean }>>(`/admin/community/posts/${postId}/recommend`, { is_recommended }),

  deletePost: (postId: string) =>
    api.delete<SuccessData<{ id: string }>>(`/admin/community/posts/${postId}`),
};

// 话术管理
export const adminScriptApi = {
  list: (params?: { status?: string; keyword?: string; style?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedData<AdminScript>>('/admin/scripts', { params }),

  approve: (scriptId: string, action: 'approve' | 'reject', comment?: string) =>
    api.post<SuccessData<{ id: string; status: string }>>(`/admin/scripts/${scriptId}/approve`, { action, comment }),
};

// 陪练场景管理
export const adminScenarioApi = {
  list: (params?: { status?: string; category?: string; difficulty?: string; page?: number; page_size?: number }) =>
    api.get<PaginatedData<AdminScenario>>('/admin/training/scenarios', { params }),

  create: (data: Partial<AdminScenario>) =>
    api.post<SuccessData<AdminScenario>>('/admin/training/scenarios', data),

  update: (scenarioId: string, data: Partial<AdminScenario>) =>
    api.put<SuccessData<AdminScenario>>(`/admin/training/scenarios/${scenarioId}`, data),

  publish: (scenarioId: string) =>
    api.post<SuccessData<{ id: string; status: string }>>(`/admin/training/scenarios/${scenarioId}/publish`),

  delete: (scenarioId: string) =>
    api.delete<SuccessData<{ id: string }>>(`/admin/training/scenarios/${scenarioId}`),
};

// 系统设置
export const settingsApi = {
  get: () =>
    api.get<SuccessData<SystemSettings>>('/admin/settings'),

  update: (data: Partial<SystemSettings>) =>
    api.put<SuccessData<{ updated_keys: string[] }>>('/admin/settings', data),
};
