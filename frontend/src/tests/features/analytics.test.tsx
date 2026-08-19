/**
 * AnalyticsPage 组件测试（Task 32 — P2-3 Admin Component Test Coverage）。
 *
 * 覆盖数据看板关键状态：loading / error / 成功渲染（统计卡 + 报表卡标题）。
 * 策略：vi.mock adminService.analyticsApi（不触真实网络），axiosRes 包装响应形状。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AnalyticsPage } from '../../features/admin/AnalyticsPage';
import { analyticsApi } from '../../services/adminService';

vi.mock('../../services/adminService', () => ({
  adminUserApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), disable: vi.fn(), enable: vi.fn() },
  auditLogApi: { list: vi.fn() },
  analyticsApi: { overview: vi.fn(), aiUsage: vi.fn(), training: vi.fn(), community: vi.fn() },
  complianceApi: { listRules: vi.fn(), createRule: vi.fn(), updateRule: vi.fn(), listReviews: vi.fn(), processReview: vi.fn() },
  adminCommunityApi: { listPosts: vi.fn(), togglePin: vi.fn(), toggleRecommend: vi.fn(), deletePost: vi.fn() },
  adminScriptApi: { list: vi.fn(), approve: vi.fn() },
  adminScenarioApi: { list: vi.fn(), publish: vi.fn(), delete: vi.fn() },
  settingsApi: { get: vi.fn(), update: vi.fn() },
}));

const mockedOverview = vi.mocked(analyticsApi.overview);
const mockedAiUsage = vi.mocked(analyticsApi.aiUsage);
const mockedTraining = vi.mocked(analyticsApi.training);
const mockedCommunity = vi.mocked(analyticsApi.community);

function axiosRes(data: unknown): never {
  return { data } as never;
}

const overviewData = {
  period: 'month',
  user_stats: { total_users: 10, active_users: 8, new_users: 2, active_rate: 80 },
  customer_stats: { total_customers: 100, new_customers: 5, high_intent: 20, conversion_rate: 15 },
  ai_stats: { total_interactions: 500, satisfaction_rate: 95, avg_response_time_ms: 800 },
  training_stats: { total_sessions: 30, avg_score: 85, completion_rate: 90 },
  community_stats: { total_posts: 40, total_comments: 120, active_contributors: 15 },
};

const aiUsageData = {
  period: 'month', total_calls: 500, feature_breakdown: [], top_users: [],
  error_rate: 1, avg_latency_ms: 800,
  token_usage: { total_input_tokens: 1000, total_output_tokens: 500, total_tokens: 1500 },
};

const trainingData = {
  period: 'month', total_sessions: 30, avg_score: 85, completion_rate: 90,
  scenario_popularity: [], score_distribution: [],
};

const communityData = {
  period: 'month', total_posts: 40, total_comments: 120, active_contributors: 15,
  category_distribution: [], top_posts: [],
};

function resolveAll() {
  mockedOverview.mockResolvedValue(axiosRes({ data: overviewData }));
  mockedAiUsage.mockResolvedValue(axiosRes({ data: aiUsageData }));
  mockedTraining.mockResolvedValue(axiosRes({ data: trainingData }));
  mockedCommunity.mockResolvedValue(axiosRes({ data: communityData }));
}

describe('AnalyticsPage（数据看板）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading：显示加载指示', () => {
    mockedOverview.mockReturnValue(new Promise(() => {}));
    mockedAiUsage.mockReturnValue(new Promise(() => {}));
    mockedTraining.mockReturnValue(new Promise(() => {}));
    mockedCommunity.mockReturnValue(new Promise(() => {}));
    render(<AnalyticsPage />);
    expect(screen.getByText('正在加载数据...')).toBeInTheDocument();
  });

  it('error：展示错误提示（不崩溃）', async () => {
    mockedOverview.mockRejectedValue(new Error('boom'));
    mockedAiUsage.mockRejectedValue(new Error('boom'));
    mockedTraining.mockRejectedValue(new Error('boom'));
    mockedCommunity.mockRejectedValue(new Error('boom'));
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('加载数据失败，请重试')).toBeInTheDocument();
    });
  });

  it('success：统计卡与报表卡标题渲染', async () => {
    resolveAll();
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('AI 使用情况')).toBeInTheDocument();
    });
    expect(screen.getByText('培训数据')).toBeInTheDocument();
    expect(screen.getByText('社区热门帖子')).toBeInTheDocument();
    // 统计卡（总用户数等）渲染
    expect(screen.getAllByText(/总用户数|AI 交互次数|社区帖子/).length).toBeGreaterThan(0);
  });

  it('empty：数据为空时展示暂无数据（不崩溃）', async () => {
    mockedOverview.mockResolvedValue(axiosRes({ data: null }));
    mockedAiUsage.mockResolvedValue(axiosRes({ data: null }));
    mockedTraining.mockResolvedValue(axiosRes({ data: null }));
    mockedCommunity.mockResolvedValue(axiosRes({ data: null }));
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getAllByText('暂无数据').length).toBeGreaterThan(0);
    });
  });
});
