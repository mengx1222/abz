/**
 * CompliancePage 组件测试（Task 24 — P2-3 Admin 页面测试覆盖扩展）。
 *
 * 覆盖合规中心两个 Tab 的关键状态：
 * - RulesTab: loading / error / empty / 列表渲染 / toggle mutation（toast + loading 防重复）
 * - ReviewsTab: 列表渲染 / approve mutation / error
 * 策略：vi.mock adminService.complianceApi（不触真实网络），断言 UI 与 toast。
 *
 * 注意：complianceApi 方法返回 AxiosResponse（页面内 res.data.data 解包），
 * mock resolved value 必须包 { data: ... } 形状（helper axiosRes）。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useToastStore } from '../../hooks/useToast';
import { CompliancePage } from '../../features/admin/CompliancePage';
import {
  complianceApi,
  type ComplianceRule,
  type ComplianceReview,
} from '../../services/adminService';

vi.mock('../../services/adminService', () => ({
  complianceApi: {
    listRules: vi.fn(),
    updateRule: vi.fn(),
    listReviews: vi.fn(),
    processReview: vi.fn(),
  },
}));

const mockedListRules = vi.mocked(complianceApi.listRules);
const mockedUpdateRule = vi.mocked(complianceApi.updateRule);
const mockedListReviews = vi.mocked(complianceApi.listReviews);
const mockedProcessReview = vi.mocked(complianceApi.processReview);

/** 将纯数据包装为 axios response 形状（mock 专用；返回 never 以兼容任意泛型）。 */
function axiosRes(data: unknown): never {
  return { data } as never;
}

const mockRule: ComplianceRule = {
  id: 'rule-1',
  name: '严禁承诺收益',
  description: '禁止向客户承诺确定收益',
  category: '话术',
  severity: 'violation',
  severity_label: '违规',
  keywords: ['收益', '保证'],
  patterns: [],
  is_active: true,
};

const mockReview: ComplianceReview = {
  id: 'rv-1',
  type: 'script',
  type_label: '话术',
  title: '话术：医疗险推荐',
  content_preview: '该产品收益稳定...',
  author_name: '张三',
  severity: 'warning',
  status: 'pending',
  priority: 'high',
};

function clearToasts() {
  useToastStore.setState({ toasts: [] });
}

function rulesPageData() {
  return {
    success: true,
    data: [mockRule],
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    request_id: 'req-1',
  };
}

function reviewsPageData() {
  return {
    success: true,
    data: [mockReview],
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    request_id: 'req-2',
  };
}

describe('CompliancePage（合规中心）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearToasts();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ---- RulesTab ----

  it('rules loading：显示加载指示', async () => {
    mockedListRules.mockReturnValue(new Promise(() => {}));
    render(<CompliancePage />);

    expect(screen.getByText('加载合规规则...')).toBeInTheDocument();
  });

  it('rules error：展示错误与重新加载', async () => {
    mockedListRules.mockRejectedValue(new Error('boom'));
    render(<CompliancePage />);

    await waitFor(() => {
      expect(screen.getByText('加载合规规则失败，请重试')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument();
  });

  it('rules empty：无规则时展示空状态', async () => {
    mockedListRules.mockResolvedValue(axiosRes({ ...rulesPageData(), data: [] }));
    render(<CompliancePage />);

    await waitFor(() => {
      expect(screen.getByText('暂无合规规则')).toBeInTheDocument();
    });
  });

  it('rules list：渲染规则卡片（名称/严重级别/启用状态）', async () => {
    mockedListRules.mockResolvedValue(axiosRes(rulesPageData()));
    render(<CompliancePage />);

    await waitFor(() => {
      expect(screen.getByText('严禁承诺收益')).toBeInTheDocument();
    });
    expect(screen.getByText('违规')).toBeInTheDocument();
    expect(screen.getByText('已启用')).toBeInTheDocument();
  });

  it('rules toggle：停用规则调用 updateRule 并 toast 成功', async () => {
    mockedListRules.mockResolvedValue(axiosRes(rulesPageData()));
    mockedUpdateRule.mockResolvedValue(axiosRes({ success: true, data: mockRule }));
    render(<CompliancePage />);

    await waitFor(() => screen.getByText('严禁承诺收益'));

    // 开关按钮（含 relative inline-flex class 的 button）
    const toggle = screen.getAllByRole('button').find((b) =>
      b.className.includes('relative inline-flex')
    );
    expect(toggle).toBeTruthy();
    fireEvent.click(toggle!);

    await waitFor(() => {
      expect(mockedUpdateRule).toHaveBeenCalledWith('rule-1', { is_active: false });
      const toast = useToastStore.getState().toasts.find((t) =>
        t.title.includes('已停用规则')
      );
      expect(toast?.variant).toBe('success');
    });
  });

  // ---- ReviewsTab ----

  it('reviews list：切到审核列表并渲染待审核内容', async () => {
    mockedListRules.mockResolvedValue(axiosRes({ ...rulesPageData(), data: [] }));
    mockedListReviews.mockResolvedValue(axiosRes(reviewsPageData()));
    render(<CompliancePage />);

    await waitFor(() => screen.getByText('暂无合规规则'));
    fireEvent.click(screen.getByText('审核列表'));

    await waitFor(() => {
      expect(screen.getByText('话术：医疗险推荐')).toBeInTheDocument();
    });
    expect(screen.getByText('待审核')).toBeInTheDocument();
    expect(screen.getByText(/作者：张三/)).toBeInTheDocument();
  });

  it('reviews approve：通过审核调用 processReview 并 toast 成功', async () => {
    mockedListRules.mockResolvedValue(axiosRes({ ...rulesPageData(), data: [] }));
    mockedListReviews.mockResolvedValue(axiosRes(reviewsPageData()));
    mockedProcessReview.mockResolvedValue(axiosRes({ success: true, data: mockReview }));
    render(<CompliancePage />);

    await waitFor(() => screen.getByText('暂无合规规则'));
    fireEvent.click(screen.getByText('审核列表'));
    await waitFor(() => screen.getByText('话术：医疗险推荐'));

    fireEvent.click(screen.getByRole('button', { name: '通过' }));

    await waitFor(() => {
      expect(mockedProcessReview).toHaveBeenCalledWith('rv-1', 'approve', '审核通过');
      const toast = useToastStore.getState().toasts.find((t) => t.title === '已通过审核');
      expect(toast?.variant).toBe('success');
    });
  });

  it('reviews error：加载失败展示错误', async () => {
    mockedListRules.mockResolvedValue(axiosRes({ ...rulesPageData(), data: [] }));
    mockedListReviews.mockRejectedValue(new Error('boom'));
    render(<CompliancePage />);

    await waitFor(() => screen.getByText('暂无合规规则'));
    fireEvent.click(screen.getByText('审核列表'));

    await waitFor(() => {
      expect(screen.getByText('加载审核列表失败，请重试')).toBeInTheDocument();
    });
  });
});
