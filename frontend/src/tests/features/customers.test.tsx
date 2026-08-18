/**
 * CustomersPage 组件测试（Task 24 — P2-3 Admin/核心业务页面测试覆盖扩展）。
 *
 * 覆盖客户列表页关键状态：
 * - loading / error / empty / 列表渲染（姓名、总数）
 * - 删除 mutation（confirm → deleteCustomer + toast 成功）
 * - 分页渲染（totalPages > 1 时显示页码）
 * 策略：vi.mock customerService + MemoryRouter（页面使用 useNavigate）。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useToastStore } from '../../hooks/useToast';
import { CustomersPage } from '../../features/customers/CustomersPage';
import {
  listCustomers,
  deleteCustomer,
  type Customer,
} from '../../services/customerService';

vi.mock('../../services/customerService', () => ({
  listCustomers: vi.fn(),
  deleteCustomer: vi.fn(),
  createCustomer: vi.fn(),
  updateCustomer: vi.fn(),
  getCustomer: vi.fn(),
}));

const mockedListCustomers = vi.mocked(listCustomers);
const mockedDeleteCustomer = vi.mocked(deleteCustomer);

const mockCustomer: Customer = {
  id: 'c-1',
  name: '张先生',
  age: 42,
  gender: 'male',
  phone: '13900001111',
  customer_type: 'active',
  tags: ['VIP'],
  insurance_type: '医疗险',
  current_stage: 'needs_analysis',
  intention_level: 3,
  source_channel: '转介绍',
  notes: null,
  assigned_to: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
};

function listResult(items: Customer[], total: number, totalPages: number) {
  return { items, total, page: 1, pageSize: 20, totalPages };
}

function clearToasts() {
  useToastStore.setState({ toasts: [] });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <CustomersPage />
    </MemoryRouter>
  );
}

describe('CustomersPage（客户360）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearToasts();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loading：显示加载指示', async () => {
    mockedListCustomers.mockReturnValue(new Promise(() => {}));
    renderPage();

    expect(screen.getByText('加载客户列表...')).toBeInTheDocument();
  });

  it('error：展示错误与重新加载', async () => {
    mockedListCustomers.mockRejectedValue(new Error('boom'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('加载客户列表失败，请重试')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument();
  });

  it('empty：无匹配客户时展示空状态', async () => {
    mockedListCustomers.mockResolvedValue(listResult([], 0, 1));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('未找到匹配的客户')).toBeInTheDocument();
    });
  });

  it('list：渲染客户姓名与总数', async () => {
    mockedListCustomers.mockResolvedValue(listResult([mockCustomer], 1, 1));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('张先生')).toBeInTheDocument();
    });
    expect(screen.getByText(/共 1 位客户/)).toBeInTheDocument();
  });

  it('delete：confirm 后调用 deleteCustomer 并 toast 成功', async () => {
    mockedListCustomers.mockResolvedValue(listResult([mockCustomer], 1, 1));
    mockedDeleteCustomer.mockResolvedValue();
    renderPage();

    await waitFor(() => screen.getByText('张先生'));
    fireEvent.click(screen.getByRole('button', { name: '删除' }));

    await waitFor(() => {
      expect(mockedDeleteCustomer).toHaveBeenCalledWith('c-1');
      const toast = useToastStore.getState().toasts.find((t) => t.title === '已删除');
      expect(toast?.variant).toBe('success');
    });
  });

  it('pagination：多页时渲染页码', async () => {
    mockedListCustomers.mockResolvedValue(listResult([mockCustomer], 21, 2));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('1 / 2')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '上一页' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '下一页' })).not.toBeDisabled();
  });
});
