/**
 * UsersPage 组件测试（Task 32 — P2-3 Admin Component Test Coverage）。
 *
 * 覆盖用户管理页关键状态：loading / error / empty / 列表渲染 / 禁用 mutation。
 * 策略：vi.mock adminService.adminUserApi（不触真实网络），axiosRes 包装响应形状。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useToastStore } from '../../hooks/useToast';
import { UsersPage } from '../../features/admin/UsersPage';
import { adminUserApi, type AdminUser } from '../../services/adminService';

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

const mockedList = vi.mocked(adminUserApi.list);
const mockedDisable = vi.mocked(adminUserApi.disable);

function axiosRes(data: unknown): never {
  return { data } as never;
}

const mockUser: AdminUser = {
  id: 'u-1',
  phone: '13800138000',
  name: '林思远',
  role_code: 'AGENT',
  role_name: '代理人',
  organization_name: '上海分公司-浦东团队',
  status: 'active',
  last_login_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
};

function pageData() {
  return {
    success: true,
    data: [mockUser],
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    request_id: 'req-1',
  };
}

function clearToasts() {
  useToastStore.setState({ toasts: [] });
}

describe('UsersPage（用户管理）', () => {
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
    render(<UsersPage />);
    expect(screen.getByText('加载用户列表...')).toBeInTheDocument();
  });

  it('error：展示错误与重新加载', async () => {
    mockedList.mockRejectedValue(new Error('boom'));
    render(<UsersPage />);
    await waitFor(() => {
      expect(screen.getByText('加载用户列表失败，请重试')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument();
  });

  it('empty：无用户时展示空状态', async () => {
    mockedList.mockResolvedValue(axiosRes({ ...pageData(), data: [] }));
    render(<UsersPage />);
    await waitFor(() => {
      expect(screen.getByText('未找到匹配的用户')).toBeInTheDocument();
    });
  });

  it('list：渲染用户名、手机号与角色', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    render(<UsersPage />);
    await waitFor(() => {
      expect(screen.getByText('林思远')).toBeInTheDocument();
    });
    expect(screen.getByText('13800138000')).toBeInTheDocument();
    expect(screen.getAllByText('代理人').length).toBeGreaterThan(0);
  });

  it('disable mutation：点击禁用调用 disable 并 toast 成功', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    mockedDisable.mockResolvedValue(axiosRes({ success: true, data: { id: 'u-1' } }));
    render(<UsersPage />);
    await waitFor(() => screen.getByText('林思远'));
    fireEvent.click(screen.getByRole('button', { name: '禁用' }));
    await waitFor(() => {
      expect(mockedDisable).toHaveBeenCalledWith('u-1', '管理员操作');
      const toast = useToastStore.getState().toasts.find((t) =>
        t.title.includes('已禁用用户')
      );
      expect(toast?.variant).toBe('success');
    });
  });
});
