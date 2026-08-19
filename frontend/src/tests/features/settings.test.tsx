/**
 * SettingsPage 组件测试（Task 32 — P2-3 Admin Component Test Coverage）。
 *
 * 覆盖系统设置页关键状态：loading / error / 成功渲染（各设置组标题）。
 * 策略：vi.mock adminService.settingsApi（不触真实网络），axiosRes 包装响应形状。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SettingsPage } from '../../features/admin/SettingsPage';
import { settingsApi } from '../../services/adminService';

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

const mockedGet = vi.mocked(settingsApi.get);

function axiosRes(data: unknown): never {
  return { data } as never;
}

const settingsData = {
  ai: { default_model: 'qwen-plus', max_tokens: 4096, temperature: 0.7 },
  rag: { top_k: 5, embedding_model: 'text-embedding-v3' },
  compliance: { auto_check_enabled: true },
  notification: { email_enabled: true },
  community: { moderation_enabled: true },
};

describe('SettingsPage（系统设置）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading：显示加载指示', () => {
    mockedGet.mockReturnValue(new Promise(() => {}));
    render(<SettingsPage />);
    expect(screen.getByText('正在加载设置...')).toBeInTheDocument();
  });

  it('error：展示错误提示（不崩溃）', async () => {
    mockedGet.mockRejectedValue(new Error('boom'));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('加载系统设置失败，请重试')).toBeInTheDocument();
    });
  });

  it('success：各设置组标题渲染', async () => {
    mockedGet.mockResolvedValue(axiosRes({ data: settingsData }));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('AI 设置')).toBeInTheDocument();
    });
    expect(screen.getByText('RAG 设置')).toBeInTheDocument();
    expect(screen.getByText('合规设置')).toBeInTheDocument();
    expect(screen.getByText('通知设置')).toBeInTheDocument();
    expect(screen.getByText('社区设置')).toBeInTheDocument();
  });
});
