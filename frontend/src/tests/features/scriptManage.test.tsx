/**
 * ScriptManagePage 组件测试（Task 25 — Admin Frontend Quality & Test Coverage）。
 *
 * 覆盖话术管理页关键状态：
 * - loading / error / empty / 列表渲染（标题、风格、合规状态、审核状态）
 * - approve / reject mutation（adminScriptApi.approve + toast + loading 防重复）
 * 策略：vi.mock adminService.adminScriptApi（不触真实网络），断言 UI 与 toast。
 * 注意：adminScriptApi 返回 AxiosResponse（页面 res.data.data 解包），
 * mock resolved value 需包 { data: ... } 形状（helper axiosRes）。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useToastStore } from '../../hooks/useToast';
import { ScriptManagePage } from '../../features/admin/ScriptManagePage';
import {
  adminScriptApi,
  type AdminScript,
} from '../../services/adminService';

vi.mock('../../services/adminService', () => ({
  adminScriptApi: {
    list: vi.fn(),
    approve: vi.fn(),
  },
}));

const mockedList = vi.mocked(adminScriptApi.list);
const mockedApprove = vi.mocked(adminScriptApi.approve);

/** 将纯数据包装为 axios response 形状（mock 专用；返回 never 以兼容任意泛型）。 */
function axiosRes(data: unknown): never {
  return { data } as never;
}

const mockPendingScript: AdminScript = {
  id: 'script-1',
  title: '百万医疗险价格异议话术',
  style: 'professional',
  style_label: '专业',
  product_type: '医疗险',
  content_preview: '陈先生，我为您做一个成本效益分析...',
  author_name: '李四',
  status: 'pending',
  compliance_status: 'GREEN',
  usage_count: 12,
  favorite_count: 3,
  created_at: '2026-01-01T00:00:00Z',
};

function pageData() {
  return {
    success: true,
    data: [mockPendingScript],
    pagination: { page: 1, page_size: 10, total: 1, total_pages: 1 },
    request_id: 'req-1',
  };
}

function clearToasts() {
  useToastStore.setState({ toasts: [] });
}

describe('ScriptManagePage（话术管理）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearToasts();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loading：显示加载指示', async () => {
    mockedList.mockReturnValue(new Promise(() => {}));
    render(<ScriptManagePage />);

    expect(screen.getByText('正在加载话术...')).toBeInTheDocument();
  });

  it('error：展示加载失败', async () => {
    mockedList.mockRejectedValue(new Error('boom'));
    render(<ScriptManagePage />);

    await waitFor(() => {
      expect(screen.getByText('加载话术列表失败，请重试')).toBeInTheDocument();
    });
  });

  it('empty：无话术时展示空状态', async () => {
    mockedList.mockResolvedValue(axiosRes({ ...pageData(), data: [] }));
    render(<ScriptManagePage />);

    await waitFor(() => {
      expect(screen.getByText('暂无话术记录')).toBeInTheDocument();
    });
  });

  it('list：渲染话术标题、风格、合规与审核状态', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    render(<ScriptManagePage />);

    await waitFor(() => {
      expect(screen.getByText('百万医疗险价格异议话术')).toBeInTheDocument();
    });
    expect(screen.getByText('李四')).toBeInTheDocument();
    // 「专业」「合规」「待审核」同时出现在筛选下拉与 badge → 用 getAllByText 断言存在
    expect(screen.getAllByText('专业').length).toBeGreaterThan(0);
    expect(screen.getAllByText('合规').length).toBeGreaterThan(0);
    expect(screen.getAllByText('待审核').length).toBeGreaterThan(0);
  });

  it('approve mutation：点击通过调用 approve(approve) 并 toast 成功', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    mockedApprove.mockResolvedValue(axiosRes({ success: true, data: { id: 'script-1', status: 'approved' } }));
    render(<ScriptManagePage />);

    await waitFor(() => screen.getByText('百万医疗险价格异议话术'));
    fireEvent.click(screen.getByRole('button', { name: '通过' }));

    await waitFor(() => {
      expect(mockedApprove).toHaveBeenCalledWith('script-1', 'approve');
      const toast = useToastStore.getState().toasts.find((t) =>
        t.description === '话术已通过审核'
      );
      expect(toast?.variant).toBe('success');
    });
  });

  it('reject mutation：点击拒绝调用 approve(reject) 并 toast 成功', async () => {
    mockedList.mockResolvedValue(axiosRes(pageData()));
    mockedApprove.mockResolvedValue(axiosRes({ success: true, data: { id: 'script-1', status: 'rejected' } }));
    render(<ScriptManagePage />);

    await waitFor(() => screen.getByText('百万医疗险价格异议话术'));
    fireEvent.click(screen.getByRole('button', { name: '拒绝' }));

    await waitFor(() => {
      expect(mockedApprove).toHaveBeenCalledWith('script-1', 'reject');
      const toast = useToastStore.getState().toasts.find((t) =>
        t.description === '话术已拒绝'
      );
      expect(toast?.variant).toBe('success');
    });
  });
});
