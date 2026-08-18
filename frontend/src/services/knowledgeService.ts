/**
 * 知识库管理 API Service（Task 23 — Production 对接）
 *
 * 覆盖 Task 21/22 全部 KB + Document 管理 endpoints：
 * - KB: list / create / get / update / delete
 * - Document: list / detail / upload / publish / unpublish / delete
 *
 * 错误语义：后端 FastAPI 错误为 { detail: { code, message } }，
 * 404 = 不可见/不存在，403 = 可见但无写权限；getErrorMessage 提取 message 供 UI 展示。
 */
import api from './api';

// ---- Types ----

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  category: string;
  status: string;
  document_count: number;
  total_chunks: number;
  is_public: boolean;
  allowed_roles: string[] | null;
  version: number;
  metadata?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  knowledge_base_id: string;
  title: string;
  file_name: string | null;
  file_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  parse_error: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UploadResult {
  document_id: string;
  title: string;
  status: string;
  chunks_count: number;
  message: string;
}

// ---- Error helpers ----

/** 从 axios 错误中提取后端 detail.message（404/403 语义展示用）。 */
export function getErrorMessage(err: unknown, fallback = '操作失败'): string {
  if (
    err &&
    typeof err === 'object' &&
    'response' in err &&
    err.response &&
    typeof err.response === 'object' &&
    'data' in err.response &&
    err.response.data &&
    typeof err.response.data === 'object' &&
    'detail' in err.response.data &&
    err.response.data.detail &&
    typeof err.response.data.detail === 'object' &&
    'message' in err.response.data.detail
  ) {
    const msg = (err.response.data.detail as { message?: string }).message;
    if (msg) return msg;
  }
  return fallback;
}

// ---- Knowledge Base API ----

export async function listKnowledgeBases(params?: {
  category?: string;
  status?: string;
}): Promise<KnowledgeBase[]> {
  const query = new URLSearchParams();
  if (params?.category) query.set('category', params.category);
  if (params?.status) query.set('status', params.status);

  const res = await api.get(`/admin/knowledge-bases?${query.toString()}`);
  return res.data;
}

export async function createKnowledgeBase(data: {
  name: string;
  description?: string;
  category?: string;
  is_public?: boolean;
}): Promise<KnowledgeBase> {
  const res = await api.post('/admin/knowledge-bases', data);
  return res.data;
}

export async function getKnowledgeBase(kbId: string): Promise<KnowledgeBase> {
  const res = await api.get(`/admin/knowledge-bases/${kbId}`);
  return res.data;
}

export async function updateKnowledgeBase(
  kbId: string,
  data: Partial<Pick<KnowledgeBase, 'name' | 'description' | 'category' | 'is_public' | 'status'>>
): Promise<KnowledgeBase> {
  const res = await api.put(`/admin/knowledge-bases/${kbId}`, data);
  return res.data;
}

export async function deleteKnowledgeBase(kbId: string): Promise<void> {
  await api.delete(`/admin/knowledge-bases/${kbId}`);
}

// ---- Document API ----

export async function listDocuments(
  kbId: string,
  params?: { status?: string }
): Promise<KnowledgeDocument[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);

  const res = await api.get(`/admin/knowledge-bases/${kbId}/documents?${query.toString()}`);
  return res.data;
}

export async function getKnowledgeDocument(
  kbId: string,
  docId: string
): Promise<KnowledgeDocument> {
  const res = await api.get(`/admin/knowledge-bases/${kbId}/documents/${docId}`);
  return res.data;
}

export async function uploadDocument(
  kbId: string,
  file: File,
  title?: string
): Promise<UploadResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);

  const res = await api.post(`/admin/knowledge-bases/${kbId}/documents/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function publishDocument(
  kbId: string,
  docId: string
): Promise<KnowledgeDocument> {
  const res = await api.post(`/admin/knowledge-bases/${kbId}/documents/${docId}/publish`);
  return res.data;
}

export async function unpublishDocument(
  kbId: string,
  docId: string
): Promise<KnowledgeDocument> {
  const res = await api.post(`/admin/knowledge-bases/${kbId}/documents/${docId}/unpublish`);
  return res.data;
}

export async function deleteDocument(
  kbId: string,
  docId: string
): Promise<void> {
  await api.delete(`/admin/knowledge-bases/${kbId}/documents/${docId}`);
}
