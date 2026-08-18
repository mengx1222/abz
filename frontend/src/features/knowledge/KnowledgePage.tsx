/**
 * 知识库管理页面
 * 
 * 功能：
 * - 知识库列表展示（卡片形式）
 * - 创建新知识库
 * - 查看知识库详情（文档列表）
 * - 上传文档
 * - 发布/删除文档
 */
import { useState, useEffect, useCallback } from 'react';
import {
  type KnowledgeBase,
  type KnowledgeDocument,
  type UploadResult,
  listKnowledgeBases,
  createKnowledgeBase,
  listDocuments,
  uploadDocument,
  publishDocument,
  deleteDocument,
  deleteKnowledgeBase,
} from '../../services/knowledgeService';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { useToast } from '../../hooks/useToast';

// ---- Category labels ----
const CATEGORY_LABELS: Record<string, string> = {
  product: '产品知识',
  regulation: '监管合规',
  training: '培训资料',
  faq: '常见问题',
};

const STATUS_VARIANTS: Record<string, 'default' | 'success' | 'warning' | 'danger'> = {
  draft: 'warning',
  active: 'success',
  published: 'success',
  archived: 'default',
  uploaded: 'default',
  parsing: 'warning',
  parsed: 'default',
  reviewing: 'warning',
  expired: 'danger',
};

export function KnowledgePage() {
  const { toast: showToast } = useToast();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newKB, setNewKB] = useState({ name: '', description: '', category: 'product', is_public: true });

  const fetchKBs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listKnowledgeBases();
      setKnowledgeBases(data);
    } catch (err) {
      showToast({ title: '加载知识库失败', variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKBs();
  }, [fetchKBs]);

  // 查看知识库详情
  const handleSelectKB = async (kb: KnowledgeBase) => {
    setSelectedKB(kb);
    try {
      const docs = await listDocuments(kb.id);
      setDocuments(docs);
    } catch (err) {
      showToast({ title: '加载文档列表失败', variant: 'error' });
    }
  };

  // 返回列表
  const handleBack = () => {
    setSelectedKB(null);
    setDocuments([]);
  };

  // 创建知识库
  const handleCreate = async () => {
    if (!newKB.name.trim()) {
      showToast({ title: '请输入知识库名称', variant: 'error' });
      return;
    }
    try {
      setCreating(true);
      await createKnowledgeBase({
        name: newKB.name.trim(),
        description: newKB.description.trim(),
        category: newKB.category,
        is_public: newKB.is_public,
      });
      showToast({ title: '知识库创建成功', variant: 'success' });
      setShowCreateForm(false);
      setNewKB({ name: '', description: '', category: 'product', is_public: true });
      fetchKBs();
    } catch (err) {
      showToast({ title: '创建失败', variant: 'error' });
    } finally {
      setCreating(false);
    }
  };

  // 上传文档
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedKB) return;

    try {
      setUploading(true);
      const result: UploadResult = await uploadDocument(selectedKB.id, file);
      showToast({ title: result.message, variant: 'success' });
      const docs = await listDocuments(selectedKB.id);
      setDocuments(docs);
      fetchKBs();
    } catch (err) {
      showToast({ title: '文档上传失败', variant: 'error' });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // 发布文档
  const handlePublish = async (doc: KnowledgeDocument) => {
    if (!selectedKB) return;
    try {
      await publishDocument(selectedKB.id, doc.id);
      showToast({ title: '文档已发布', variant: 'success' });
      const docs = await listDocuments(selectedKB.id);
      setDocuments(docs);
    } catch (err) {
      showToast({ title: '发布失败', variant: 'error' });
    }
  };

  // 删除文档
  const handleDeleteDoc = async (doc: KnowledgeDocument) => {
    if (!selectedKB) return;
    if (!confirm(`确定删除文档「${doc.title}」？`)) return;
    try {
      await deleteDocument(selectedKB.id, doc.id);
      showToast({ title: '文档已删除', variant: 'success' });
      const docs = await listDocuments(selectedKB.id);
      setDocuments(docs);
    } catch (err) {
      showToast({ title: '文档删除失败', variant: 'error' });
    }
  };

  // 删除知识库
  const handleDeleteKB = async (kb: KnowledgeBase) => {
    if (!confirm(`确定删除知识库「${kb.name}」及其所有文档？`)) return;
    try {
      await deleteKnowledgeBase(kb.id);
      showToast({ title: '知识库已删除', variant: 'success' });
      fetchKBs();
    } catch (err) {
      showToast({ title: '知识库删除失败', variant: 'error' });
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // ---- 知识库详情视图 ----
  if (selectedKB) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            ← 返回列表
          </button>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900">{selectedKB.name}</h2>
            <p className="text-sm text-gray-500 mt-1">{selectedKB.description}</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={STATUS_VARIANTS[selectedKB.status] || 'default'}>
              {selectedKB.status === 'active' ? '已激活' : selectedKB.status === 'draft' ? '草稿' : selectedKB.status}
            </Badge>
            <span className="text-sm text-gray-500">
              {selectedKB.document_count} 文档 · {selectedKB.total_chunks} 分块
            </span>
          </div>
        </div>

        {/* Upload bar */}
        <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <label className={`flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium cursor-pointer hover:bg-blue-700 transition-colors ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
            {uploading ? '上传中...' : '上传文档'}
            <input
              type="file"
              accept=".txt,.md,.json,.pdf,.docx"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
          <span className="text-sm text-gray-500">支持 TXT、Markdown、JSON、PDF 格式</span>
        </div>

        {/* Document list */}
        <div className="space-y-3">
          {documents.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p className="text-lg">暂无文档</p>
              <p className="text-sm mt-1">上传文档后，系统将自动解析并生成知识块</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-200 hover:shadow-sm transition-all"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xs font-medium ${
                    doc.file_type === 'pdf' ? 'bg-red-50 text-red-600' :
                    doc.file_type === 'json' ? 'bg-yellow-50 text-yellow-600' :
                    doc.file_type === 'md' ? 'bg-purple-50 text-purple-600' :
                    'bg-gray-50 text-gray-600'
                  }`}>
                    {doc.file_type.toUpperCase()}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{doc.title}</p>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {doc.file_name} · {formatFileSize(doc.file_size)} · {doc.chunk_count} 个知识块
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={STATUS_VARIANTS[doc.status] || 'default'}>
                    {doc.status === 'published' ? '已发布' : doc.status === 'parsed' ? '已解析' : doc.status}
                  </Badge>
                  {doc.status !== 'published' && (
                    <Button size="sm" variant="primary" onClick={() => handlePublish(doc)}>
                      发布
                    </Button>
                  )}
                  <button
                    onClick={() => handleDeleteDoc(doc)}
                    className="text-gray-400 hover:text-red-500 transition-colors text-sm"
                  >
                    删除
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  // ---- 知识库列表视图 ----
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">知识库管理</h1>
          <p className="text-gray-500 mt-1">管理保险产品知识文档，为 AI 助手提供专业知识支撑</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="warning">演示模式</Badge>
          <Button variant="primary" onClick={() => setShowCreateForm(!showCreateForm)}>
            + 新建知识库
          </Button>
        </div>
      </div>

      {/* Create form */}
      {showCreateForm && (
        <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-900">新建知识库</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称 *</label>
              <input
                type="text"
                value={newKB.name}
                onChange={(e) => setNewKB({ ...newKB, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="如：华安保险产品知识库"
                maxLength={200}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">分类</label>
              <select
                value={newKB.category}
                onChange={(e) => setNewKB({ ...newKB, category: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="product">产品知识</option>
                <option value="regulation">监管合规</option>
                <option value="training">培训资料</option>
                <option value="faq">常见问题</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              value={newKB.description}
              onChange={(e) => setNewKB({ ...newKB, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="简要描述知识库的用途和内容范围"
              rows={2}
              maxLength={2000}
            />
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={newKB.is_public}
                onChange={(e) => setNewKB({ ...newKB, is_public: e.target.checked })}
                className="rounded border-gray-300"
              />
              公开可见（全员可访问）
            </label>
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={handleCreate} loading={creating}>
              创建
            </Button>
            <Button variant="ghost" onClick={() => setShowCreateForm(false)}>
              取消
            </Button>
          </div>
        </div>
      )}

      {/* KB Cards */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : knowledgeBases.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">暂无知识库</p>
          <p className="text-sm mt-1">创建知识库并上传文档，为 AI 助手提供专业知识</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {knowledgeBases.map((kb) => (
            <div
              key={kb.id}
              className="p-5 bg-white rounded-lg border border-gray-200 hover:border-blue-200 hover:shadow-md transition-all cursor-pointer group"
              onClick={() => handleSelectKB(kb)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded font-medium">
                    {CATEGORY_LABELS[kb.category] || kb.category}
                  </span>
                  <Badge variant={STATUS_VARIANTS[kb.status] || 'default'}>
                    {kb.status === 'active' ? '已激活' : kb.status === 'draft' ? '草稿' : kb.status}
                  </Badge>
                </div>
              </div>
              <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                {kb.name}
              </h3>
              <p className="text-sm text-gray-500 mt-1 line-clamp-2">{kb.description}</p>
              <div className="flex items-center gap-4 mt-4 pt-3 border-t border-gray-100">
                <span className="text-sm text-gray-500">{kb.document_count} 文档</span>
                <span className="text-sm text-gray-500">{kb.total_chunks} 分块</span>
                <span className="text-sm text-gray-500">v{kb.version}</span>
              </div>
              <div className="flex gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteKB(kb); }}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
