/**
 * AuditLogPage 组件测试（Task 32 — P2-3 Admin Component Test Coverage）。
 *
 * 覆盖审计日志页关键状态：loading / error / empty / 列表渲染（用户名、动作）。
 * 策略：vi.mock adminService.auditLogApi（不触真实网络），axiosRes 包装响应形状。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuditLogPage } from '../../features/admin/AuditLogPage';
import { auditLogApi, type AuditLog } from '../../services/adminService';

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

const mockedList = vi.mocked(auditLogApi.list);

function axiosRes(data: unknown): never {
  return { data } as never;
}

const mockLog: AuditLog = {
  id: 'log-1',
  user_id: 'u-1',
  user_name: '林思远',
  user_role: 'AGENT',
  action: 'customer.create',
  resource_type: 'customers',
  resource_id: 'c-1',
  description: '创建客户',
  ip_address: '127.0.0.1',
  created_at: '2026-01-01T00:00:00Z',
};

function pageData() {
  return {
    success: true,
    data: [mockLog],
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    request_id: 'req-1',
  };
}

describe('AuditLogPage（审计日志）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading：显示加载指示', () => {
    mockedList.mockReturnValue(new Promise(() => {}));
    render(<AuditLogPage />);
    expect(screen.getByText('正在加载日志...')).toBeInTheDocument();
  });

  it('error：展示错误提示（不崩溃）', async () => {
    mockedList.mockRejectedValue(new Error('boom'));
    render(<AuditLogPage />);
    await waitFor(() => {
      expect(screen.getByText('加载审计日志失败，请重试')).toBeInTheDocument();
    });
  });

  it('empty：无日志时展示空状态', async () => {
    mockedList.mockResolvedValue(axiosRes({ ...pageData(), data: [] }));
    render(<AuditLogPage />);
    await waitFor(() => {
      expect(screen.getByText('暂无审计日志记录')).toBeInTheDocument();
    });
  });

  it('list：渲染用户名与操作描述', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    render(<AuditLogPage />);
    await waitFor(() => {
      expect(screen.getByText('林思远')).toBeInTheDocument();
    });
    expect(screen.getAllByText('创建客户').length).toBeGreaterThan(0);
    expect(screen.getByText('customers')).toBeInTheDocument();
  });
});
