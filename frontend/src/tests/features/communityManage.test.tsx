/**
 * CommunityManagePage 组件测试（Task 25 — Admin Frontend Quality & Test Coverage）。
 *
 * 覆盖社区管理页关键状态：
 * - loading / error / empty / 列表渲染（标题、作者、状态 badge）
 * - 置顶 mutation（togglePin + toast + loading 防重复）
 * - 删除 mutation（confirm → deletePost + toast）
 * 策略：vi.mock adminService.adminCommunityApi（不触真实网络），断言 UI 与 toast。
 * 注意：adminCommunityApi 返回 AxiosResponse（页面 res.data.data 解包），
 * mock resolved value 需包 { data: ... } 形状（helper axiosRes）。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useToastStore } from '../../hooks/useToast';
import { CommunityManagePage } from '../../features/admin/CommunityManagePage';
import {
  adminCommunityApi,
  type AdminPost,
} from '../../services/adminService';

vi.mock('../../services/adminService', () => ({
  adminCommunityApi: {
    listPosts: vi.fn(),
    togglePin: vi.fn(),
    toggleRecommend: vi.fn(),
    deletePost: vi.fn(),
  },
}));

const mockedListPosts = vi.mocked(adminCommunityApi.listPosts);
const mockedTogglePin = vi.mocked(adminCommunityApi.togglePin);
const mockedDeletePost = vi.mocked(adminCommunityApi.deletePost);

/** 将纯数据包装为 axios response 形状（mock 专用；返回 never 以兼容任意泛型）。 */
function axiosRes(data: unknown): never {
  return { data } as never;
}

const mockPost: AdminPost = {
  id: 'post-1',
  title: '百万医疗险投保攻略',
  author_name: '张三',
  category: 'knowledge',
  category_label: '知识分享',
  status: 'published',
  views_count: 120,
  likes_count: 8,
  comments_count: 3,
  is_pinned: false,
  is_recommended: false,
  created_at: '2026-01-01T00:00:00Z',
};

function pageData() {
  return {
    success: true,
    data: [mockPost],
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    request_id: 'req-1',
  };
}

function clearToasts() {
  useToastStore.setState({ toasts: [] });
}

describe('CommunityManagePage（社区管理）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearToasts();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loading：显示加载指示', async () => {
    mockedListPosts.mockReturnValue(new Promise(() => {}));
    render(<CommunityManagePage />);

    expect(screen.getByText('加载帖子列表...')).toBeInTheDocument();
  });

  it('error：展示错误与重新加载', async () => {
    mockedListPosts.mockRejectedValue(new Error('boom'));
    render(<CommunityManagePage />);

    await waitFor(() => {
      expect(screen.getByText('加载帖子列表失败，请重试')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument();
  });

  it('empty：无匹配帖子时展示空状态', async () => {
    mockedListPosts.mockResolvedValue(axiosRes({ ...pageData(), data: [] }));
    render(<CommunityManagePage />);

    await waitFor(() => {
      expect(screen.getByText('未找到匹配的帖子')).toBeInTheDocument();
    });
  });

  it('list：渲染帖子标题、作者与状态', async () => {
    mockedListPosts.mockResolvedValue(axiosRes(pageData()));
    render(<CommunityManagePage />);

    await waitFor(() => {
      expect(screen.getByText('百万医疗险投保攻略')).toBeInTheDocument();
    });
    expect(screen.getByText('张三')).toBeInTheDocument();
    // 「知识分享」「已发布」同时出现在筛选器与 badge → 用 getAllByText 断言存在
    expect(screen.getAllByText('知识分享').length).toBeGreaterThan(0);
    expect(screen.getAllByText('已发布').length).toBeGreaterThan(0);
  });

  it('pin mutation：点击置顶调用 togglePin 并 toast 成功', async () => {
    mockedListPosts.mockResolvedValue(axiosRes(pageData()));
    mockedTogglePin.mockResolvedValue(axiosRes({ success: true, data: { id: 'post-1', is_pinned: true } }));
    render(<CommunityManagePage />);

    await waitFor(() => screen.getByText('百万医疗险投保攻略'));

    // 置顶按钮（含 ThumbtackIcon 的 button，title=置顶）
    const pinBtn = screen.getByTitle('置顶');
    fireEvent.click(pinBtn);

    await waitFor(() => {
      expect(mockedTogglePin).toHaveBeenCalledWith('post-1', true);
      const toast = useToastStore.getState().toasts.find((t) =>
        t.title.includes('已置顶')
      );
      expect(toast?.variant).toBe('success');
    });
  });

  it('delete mutation：confirm 后调用 deletePost 并 toast 成功', async () => {
    mockedListPosts.mockResolvedValue(axiosRes(pageData()));
    mockedDeletePost.mockResolvedValue(axiosRes({ success: true, data: { id: 'post-1' } }));
    render(<CommunityManagePage />);

    await waitFor(() => screen.getByText('百万医疗险投保攻略'));
    fireEvent.click(screen.getByRole('button', { name: '删除' }));

    await waitFor(() => {
      expect(mockedDeletePost).toHaveBeenCalledWith('post-1');
      const toast = useToastStore.getState().toasts.find((t) => t.title === '已删除');
      expect(toast?.variant).toBe('success');
    });
  });
});
