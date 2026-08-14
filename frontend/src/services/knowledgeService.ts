/**
 * 知识库管理 API Service
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
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  knowledge_base_id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
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

// ---- API Functions ----

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
  data: Partial<KnowledgeBase>
): Promise<KnowledgeBase> {
  const res = await api.put(`/admin/knowledge-bases/${kbId}`, data);
  return res.data;
}

export async function deleteKnowledgeBase(kbId: string): Promise<void> {
  await api.delete(`/admin/knowledge-bases/${kbId}`);
}

export async function listDocuments(
  kbId: string,
  params?: { status?: string }
): Promise<KnowledgeDocument[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);

  const res = await api.get(`/admin/knowledge-bases/${kbId}/documents?${query.toString()}`);
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

export async function deleteDocument(
  kbId: string,
  docId: string
): Promise<void> {
  await api.delete(`/admin/knowledge-bases/${kbId}/documents/${docId}`);
}
