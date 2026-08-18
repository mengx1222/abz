/**
 * DashboardPage 组件测试（Task 24 — P2-3 Admin 页面测试覆盖扩展）。
 *
 * 覆盖核心状态：loading / error / 数据渲染 / 空 AI 建议（不渲染区块）。
 * 策略：vi.mock dashboardService 与 authStore（不触真实网络），断言 UI 行为。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DashboardPage } from '../../features/dashboard/DashboardPage';
import { getDashboard } from '../../services/dashboardService';

vi.mock('../../services/dashboardService', () => ({
  getDashboard: vi.fn(),
}));

vi.mock('../../stores/authStore', () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({ user: { name: '测试用户', role_name: '代理人' } }),
}));

const mockedGetDashboard = vi.mocked(getDashboard);

const baseOverview = {
  greeting: '上午好',
  user_name: '林思远',
  today_stats: [
    { label: '今日拜访', value: '3', sub: '较昨日 +1', trend: 'up' as const },
  ],
  ai_suggestions: [
    {
      id: 's1',
      title: '跟进高意向客户',
      description: '张先生对百万医疗险兴趣较高',
      tag: '推荐',
      tag_variant: 'success',
      action_url: null,
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  quick_actions: [
    { label: '客户管理', icon: '👥', path: '/customers', color: 'text-accent' },
  ],
  recent_activities: [],
  unread_notifications: 0,
};

describe('DashboardPage（仪表盘）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loading：渲染骨架屏', async () => {
    let resolve!: (v: typeof baseOverview) => void;
    mockedGetDashboard.mockReturnValue(new Promise((r) => (resolve = r)));
    const { container } = render(<DashboardPage />);

    expect(container.querySelector('.animate-pulse')).not.toBeNull();
    resolve(baseOverview);
    await waitFor(() => {
      expect(container.querySelector('.animate-pulse')).toBeNull();
    });
  });

  it('error：展示错误消息与重试按钮', async () => {
    mockedGetDashboard.mockRejectedValue(new Error('网络错误'));
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument();
  });

  it('data：渲染问候语、快捷操作、今日统计与 AI 建议', async () => {
    mockedGetDashboard.mockResolvedValue(baseOverview);
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('上午好，林思远')).toBeInTheDocument();
    });
    expect(screen.getByText('客户管理')).toBeInTheDocument();
    expect(screen.getByText('今日拜访')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('AI 今日建议')).toBeInTheDocument();
    expect(screen.getByText('跟进高意向客户')).toBeInTheDocument();
  });

  it('empty：无 AI 建议时不渲染该区块', async () => {
    mockedGetDashboard.mockResolvedValue({ ...baseOverview, ai_suggestions: [] });
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('上午好，林思远')).toBeInTheDocument();
    });
    expect(screen.queryByText('AI 今日建议')).not.toBeInTheDocument();
  });
});
