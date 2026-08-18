/**
 * KnowledgePage 组件测试（Task 23 — Admin Frontend Production 对接）
 *
 * 覆盖：KB list / Document list / Document detail / publish / unpublish /
 * delete / API error / 404/403 语义 / loading / empty state。
 *
 * 策略：vi.mock knowledgeService（不触真实网络），断言 UI 行为与 toast 反馈。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useToastStore } from '../../hooks/useToast';
import {
  KnowledgePage,
} from '../../features/knowledge/KnowledgePage';

// Mock knowledgeService
vi.mock('../../services/knowledgeService', () => ({
  listKnowledgeBases: vi.fn(),
  createKnowledgeBase: vi.fn(),
  updateKnowledgeBase: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
  listDocuments: vi.fn(),
  getKnowledgeDocument: vi.fn(),
  uploadDocument: vi.fn(),
  publishDocument: vi.fn(),
  unpublishDocument: vi.fn(),
  deleteDocument: vi.fn(),
  getErrorMessage: vi.fn((_err: unknown, fallback: string) => fallback),
}));

import {
  listKnowledgeBases,
  listDocuments,
  getKnowledgeDocument,
  publishDocument,
  unpublishDocument,
  deleteDocument,
  deleteKnowledgeBase,
  getErrorMessage,
} from '../../services/knowledgeService';

const mockedListKBs = vi.mocked(listKnowledgeBases);
const mockedListDocs = vi.mocked(listDocuments);
const mockedGetDoc = vi.mocked(getKnowledgeDocument);
const mockedPublish = vi.mocked(publishDocument);
const mockedUnpublish = vi.mocked(unpublishDocument);
const mockedDeleteDoc = vi.mocked(deleteDocument);
const mockedDeleteKB = vi.mocked(deleteKnowledgeBase);
const mockedGetErrMsg = vi.mocked(getErrorMessage);

const mockKB = {
  id: 'kb-1',
  name: '产品知识库',
  description: '保险产品文档',
  category: 'product',
  status: 'active',
  document_count: 1,
  total_chunks: 3,
  is_public: true,
  allowed_roles: null,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockDoc = {
  id: 'doc-1',
  knowledge_base_id: 'kb-1',
  title: '医疗险手册',
  file_name: 'medical.md',
  file_type: 'md',
  file_size: 2048,
  status: 'published',
  chunk_count: 3,
  parse_error: null,
  published_at: '2026-01-02T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
};

const mockDraftDoc = { ...mockDoc, id: 'doc-2', title: '草稿文档', status: 'draft', published_at: null };

/** 构造后端 404/403 错误（FastAPI { detail: { code, message } }）。 */
function apiError(status: number, message: string) {
  return { response: { status, data: { detail: { code: 'X', message } } } };
}

function clearToasts() {
  useToastStore.setState({ toasts: [] });
}

describe('KnowledgePage（知识库管理）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearToasts();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    // getErrorMessage 默认透传 fallback（测试针对性覆盖 404/403 时单独设置）
    mockedGetErrMsg.mockImplementation((_err, fallback) => fallback);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('KB list：渲染知识库卡片', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    render(<KnowledgePage />);

    await waitFor(() => {
      expect(screen.getByText('产品知识库')).toBeInTheDocument();
    });
    expect(screen.getByText('1 文档')).toBeInTheDocument();
    expect(screen.getByText('3 分块')).toBeInTheDocument();
  });

  it('KB list：empty state', async () => {
    mockedListKBs.mockResolvedValue([]);
    render(<KnowledgePage />);

    await waitFor(() => {
      expect(screen.getByText('暂无知识库')).toBeInTheDocument();
    });
  });

  it('KB list：API error 展示后端 message（不显示为系统异常）', async () => {
    mockedListKBs.mockRejectedValue(apiError(500, '数据库不可用'));
    mockedGetErrMsg.mockReturnValue('数据库不可用');
    render(<KnowledgePage />);

    await waitFor(() => {
      const toast = useToastStore.getState().toasts.find((t) => t.title === '数据库不可用');
      expect(toast?.variant).toBe('error');
    });
  });

  it('KB list：403 无权限语义', async () => {
    mockedListKBs.mockRejectedValue(apiError(403, '无权限查看知识库'));
    mockedGetErrMsg.mockReturnValue('无权限查看知识库');
    render(<KnowledgePage />);

    await waitFor(() => {
      const toast = useToastStore.getState().toasts.find((t) => t.title === '无权限查看知识库');
      expect(toast?.variant).toBe('error');
    });
  });

  it('Document list：点击知识库后渲染文档列表', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedListDocs.mockResolvedValue([mockDoc, mockDraftDoc]);
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('产品知识库'));

    await waitFor(() => {
      expect(screen.getByText('医疗险手册')).toBeInTheDocument();
    });
    expect(screen.getByText('草稿文档')).toBeInTheDocument();
    expect(mockedListDocs).toHaveBeenCalledWith('kb-1');
  });

  it('Document list：empty state', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedListDocs.mockResolvedValue([]);
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('产品知识库'));

    await waitFor(() => {
      expect(screen.getByText('暂无文档')).toBeInTheDocument();
    });
  });

  it('Document detail：点击文档进入详情视图', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedListDocs.mockResolvedValue([mockDoc]);
    mockedGetDoc.mockResolvedValue(mockDoc);
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('产品知识库'));
    await waitFor(() => screen.getByText('医疗险手册'));
    fireEvent.click(screen.getByText('医疗险手册'));

    await waitFor(() => {
      expect(mockedGetDoc).toHaveBeenCalledWith('kb-1', 'doc-1');
      expect(screen.getByText('医疗险手册')).toBeInTheDocument();
      expect(screen.getByText('medical.md')).toBeInTheDocument();
      expect(screen.getByText('已发布')).toBeInTheDocument();
    });
  });

  it('Document detail：404 展示后端 message（不泄露资源存在性）', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedListDocs.mockResolvedValue([mockDoc]);
    mockedGetDoc.mockRejectedValue(apiError(404, '文档不存在'));
    mockedGetErrMsg.mockReturnValue('文档不存在');
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('产品知识库'));
    await waitFor(() => screen.getByText('医疗险手册'));
    fireEvent.click(screen.getByText('医疗险手册'));

    await waitFor(() => {
      const toast = useToastStore.getState().toasts.find((t) => t.title === '文档不存在');
      expect(toast?.variant).toBe('error');
    });
  });

  it('publish：点击发布调用 API 并提示成功', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedListDocs.mockResolvedValue([mockDraftDoc]);
    mockedPublish.mockResolvedValue({ ...mockDraftDoc, status: 'published' });
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('产品知识库'));
    await waitFor(() => screen.getByText('草稿文档'));

    fireEvent.click(screen.getByText('发布'));

    await waitFor(() => {
      expect(mockedPublish).toHaveBeenCalledWith('kb-1', 'doc-2');
      const toast = useToastStore.getState().toasts.find((t) => t.title === '文档已发布');
      expect(toast?.variant).toBe('success');
    });
  });

  it('unpublish：已发布文档可取消发布', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedListDocs.mockResolvedValue([mockDoc]);
    mockedUnpublish.mockResolvedValue({ ...mockDoc, status: 'draft', published_at: null });
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('产品知识库'));
    await waitFor(() => screen.getByText('医疗险手册'));

    fireEvent.click(screen.getByText('取消发布'));

    await waitFor(() => {
      expect(mockedUnpublish).toHaveBeenCalledWith('kb-1', 'doc-1');
      const toast = useToastStore.getState().toasts.find((t) => t.title === '文档已取消发布');
      expect(toast?.variant).toBe('success');
    });
  });

  it('delete document：confirm 确认后调用删除 API', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedListDocs.mockResolvedValue([mockDoc]);
    mockedDeleteDoc.mockResolvedValue();
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('产品知识库'));
    await waitFor(() => screen.getByText('医疗险手册'));

    fireEvent.click(screen.getByText('删除'));

    await waitFor(() => {
      expect(mockedDeleteDoc).toHaveBeenCalledWith('kb-1', 'doc-1');
      const toast = useToastStore.getState().toasts.find((t) => t.title === '文档已删除');
      expect(toast?.variant).toBe('success');
    });
  });

  it('delete document：403 无权限展示后端 message', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedListDocs.mockResolvedValue([mockDoc]);
    mockedDeleteDoc.mockRejectedValue(apiError(403, '无权限删除该文档'));
    mockedGetErrMsg.mockReturnValue('无权限删除该文档');
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('产品知识库'));
    await waitFor(() => screen.getByText('医疗险手册'));
    fireEvent.click(screen.getByText('删除'));

    await waitFor(() => {
      const toast = useToastStore.getState().toasts.find((t) => t.title === '无权限删除该文档');
      expect(toast?.variant).toBe('error');
    });
  });

  it('delete KB：confirm 确认后调用删除 API', async () => {
    mockedListKBs.mockResolvedValue([mockKB]);
    mockedDeleteKB.mockResolvedValue();
    render(<KnowledgePage />);

    await waitFor(() => screen.getByText('产品知识库'));
    fireEvent.click(screen.getByText('删除'));

    await waitFor(() => {
      expect(mockedDeleteKB).toHaveBeenCalledWith('kb-1');
      const toast = useToastStore.getState().toasts.find((t) => t.title === '知识库已删除');
      expect(toast?.variant).toBe('success');
    });
  });
});
