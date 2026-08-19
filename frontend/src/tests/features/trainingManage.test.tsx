/**
 * TrainingManagePage 组件测试（Task 32 — P2-3 Admin Component Test Coverage）。
 *
 * 覆盖陪练场景管理页关键状态：loading / error / empty / 列表渲染 / 发布 mutation。
 * 策略：vi.mock adminService.adminScenarioApi（不触真实网络），axiosRes 包装响应形状。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useToastStore } from '../../hooks/useToast';
import { TrainingManagePage } from '../../features/admin/TrainingManagePage';
import { adminScenarioApi, type AdminScenario } from '../../services/adminService';

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

const mockedList = vi.mocked(adminScenarioApi.list);
const mockedPublish = vi.mocked(adminScenarioApi.publish);
const mockedDelete = vi.mocked(adminScenarioApi.delete);

function axiosRes(data: unknown): never {
  return { data } as never;
}

const mockScenario: AdminScenario = {
  id: 'scn-1',
  title: '"太贵了" — 重疾险价格犹豫',
  description: '客户对保费价格犹豫的场景',
  category: 'objection',
  difficulty: 'medium',
  status: 'published',
  duration_minutes: 10,
  usage_count: 3,
  avg_score: 85,
  tags: ['重疾险'],
};

function pageData() {
  return {
    success: true,
    data: [mockScenario],
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    request_id: 'req-1',
  };
}

function clearToasts() {
  useToastStore.setState({ toasts: [] });
}

describe('TrainingManagePage（陪练场景管理）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearToasts();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loading：显示加载指示', () => {
    mockedList.mockReturnValue(new Promise(() => {}));
    render(<TrainingManagePage />);
    expect(screen.getByText('加载场景列表...')).toBeInTheDocument();
  });

  it('error：展示错误与重新加载', async () => {
    mockedList.mockRejectedValue(new Error('boom'));
    render(<TrainingManagePage />);
    await waitFor(() => {
      expect(screen.getByText('加载场景列表失败，请重试')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument();
  });

  it('empty：无场景时展示空状态', async () => {
    mockedList.mockResolvedValue(axiosRes({ ...pageData(), data: [] }));
    render(<TrainingManagePage />);
    await waitFor(() => {
      expect(screen.getByText('未找到匹配的场景')).toBeInTheDocument();
    });
  });

  it('list：渲染场景标题与状态', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    render(<TrainingManagePage />);
    await waitFor(() => {
      expect(screen.getByText('"太贵了" — 重疾险价格犹豫')).toBeInTheDocument();
    });
    expect(screen.getAllByText('已发布').length).toBeGreaterThan(0);
  });

  it('publish mutation：点击发布调用 publish 并 toast 成功', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    mockedPublish.mockResolvedValue(axiosRes({ success: true, data: { id: 'scn-1' } }));
    render(<TrainingManagePage />);
    await waitFor(() => screen.getByText('"太贵了" — 重疾险价格犹豫'));
    fireEvent.click(screen.getByRole('button', { name: '发布' }));
    await waitFor(() => {
      expect(mockedPublish).toHaveBeenCalledWith('scn-1');
      const toast = useToastStore.getState().toasts.find((t) =>
        t.title.includes('已发布场景')
      );
      expect(toast?.variant).toBe('success');
    });
  });

  it('delete mutation：confirm 后调用 delete 并 toast 成功', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    mockedDelete.mockResolvedValue(axiosRes({ success: true, data: { id: 'scn-1' } }));
    render(<TrainingManagePage />);
    await waitFor(() => screen.getByText('"太贵了" — 重疾险价格犹豫'));
    fireEvent.click(screen.getByRole('button', { name: '删除' }));
    await waitFor(() => {
      expect(mockedDelete).toHaveBeenCalledWith('scn-1');
      const toast = useToastStore.getState().toasts.find((t) => t.title === '已删除');
      expect(toast?.variant).toBe('success');
    });
  });
});
