/**
 * 知识库管理页面（Task 23 — Production API 对接）
 *
 * 功能：
 * - 知识库列表展示（卡片形式）+ 创建/编辑/删除（真实 API）
 * - 查看知识库详情（文档列表）
 * - 文档详情查看 / 上传 / 发布 / 取消发布 / 删除
 * - 404/403 语义：toast 展示后端 detail.message（不显示为系统异常）
 * - mutation 均有 loading/防重复；删除/取消发布走 ConfirmDialog 确认机制
 *
 * 数据来源：真实后端 API（Task 21/22 DB-backed）；无 mock fallback。
 * 「演示模式」Badge 仅 VITE_APP_ENV==='demo' 时显示。
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  type KnowledgeBase,
  type KnowledgeDocument,
  type UploadResult,
  listKnowledgeBases,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  listDocuments,
  getKnowledgeDocument,
  uploadDocument,
  publishDocument,
  unpublishDocument,
  deleteDocument,
  getErrorMessage,
} from '../../services/knowledgeService';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Card, CardTitle } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Textarea } from '../../components/ui/Textarea';
import { PageHeader } from '../../components/ui/PageHeader';
import { EmptyState } from '../../components/ui/EmptyState';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { Upload, LibraryBig, FileText } from 'lucide-react';
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

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  active: '已激活',
  published: '已发布',
  archived: '已归档',
  uploaded: '已上传',
  parsing: '解析中',
  parsed: '已解析',
  reviewing: '审核中',
  expired: '已过期',
};

/** 文件类型图标底色：语义 token 化 */
const FILE_TYPE_STYLES: Record<string, string> = {
  pdf: 'bg-error/10 text-error',
  json: 'bg-warning/10 text-warning',
  md: 'bg-accent/10 text-accent',
};
const FILE_TYPE_FALLBACK_STYLE = 'bg-surface text-muted';

/** 演示模式标识：仅 demo 环境显示（生产不显示，避免误导）。 */
const isDemoEnv = import.meta.env.VITE_APP_ENV === 'demo';

export function KnowledgePage() {
  const { toast: showToast } = useToast();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [savingKB, setSavingKB] = useState(false);
  const [docLoading, setDocLoading] = useState(false);
  const [publishingDocId, setPublishingDocId] = useState<string | null>(null);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [deletingKbId, setDeletingKbId] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [editingKB, setEditingKB] = useState<KnowledgeBase | null>(null);
  const [newKB, setNewKB] = useState({ name: '', description: '', category: 'product', is_public: true });

  // 待确认操作目标（替代原生 window.confirm）
  const [pendingUnpublish, setPendingUnpublish] = useState<KnowledgeDocument | null>(null);
  const [pendingDeleteDoc, setPendingDeleteDoc] = useState<KnowledgeDocument | null>(null);
  const [pendingDeleteKB, setPendingDeleteKB] = useState<KnowledgeBase | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchKBs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listKnowledgeBases();
      setKnowledgeBases(data);
    } catch (err) {
      showToast({ title: getErrorMessage(err, '加载知识库失败'), variant: 'error' });
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
    setSelectedDoc(null);
    try {
      const docs = await listDocuments(kb.id);
      setDocuments(docs);
    } catch (err) {
      showToast({ title: getErrorMessage(err, '加载文档列表失败'), variant: 'error' });
    }
  };

  // 返回知识库列表
  const handleBack = () => {
    setSelectedKB(null);
    setSelectedDoc(null);
    setDocuments([]);
  };

  // 查看文档详情
  const handleSelectDoc = async (doc: KnowledgeDocument) => {
    if (!selectedKB) return;
    try {
      setDocLoading(true);
      const detail = await getKnowledgeDocument(selectedKB.id, doc.id);
      setSelectedDoc(detail);
    } catch (err) {
      showToast({ title: getErrorMessage(err, '加载文档详情失败'), variant: 'error' });
    } finally {
      setDocLoading(false);
    }
  };

  // 返回文档列表
  const handleBackFromDoc = () => {
    setSelectedDoc(null);
  };

  // 打开创建表单
  const openCreateForm = () => {
    setEditingKB(null);
    setNewKB({ name: '', description: '', category: 'product', is_public: true });
    setShowCreateForm(true);
  };

  // 打开编辑表单
  const openEditForm = (kb: KnowledgeBase) => {
    setEditingKB(kb);
    setNewKB({
      name: kb.name,
      description: kb.description || '',
      category: kb.category,
      is_public: kb.is_public,
    });
    setShowCreateForm(true);
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
      fetchKBs();
    } catch (err) {
      showToast({ title: getErrorMessage(err, '创建失败'), variant: 'error' });
    } finally {
      setCreating(false);
    }
  };

  // 更新知识库（编辑）
  const handleUpdate = async () => {
    if (!editingKB) return;
    if (!newKB.name.trim()) {
      showToast({ title: '请输入知识库名称', variant: 'error' });
      return;
    }
    try {
      setSavingKB(true);
      await updateKnowledgeBase(editingKB.id, {
        name: newKB.name.trim(),
        description: newKB.description.trim(),
        category: newKB.category,
        is_public: newKB.is_public,
      });
      showToast({ title: '知识库已更新', variant: 'success' });
      setShowCreateForm(false);
      setEditingKB(null);
      fetchKBs();
      if (selectedKB && selectedKB.id === editingKB.id) {
        setSelectedKB({ ...selectedKB, name: newKB.name.trim(), description: newKB.description.trim(), category: newKB.category, is_public: newKB.is_public });
      }
    } catch (err) {
      showToast({ title: getErrorMessage(err, '更新失败'), variant: 'error' });
    } finally {
      setSavingKB(false);
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
      showToast({ title: getErrorMessage(err, '文档上传失败'), variant: 'error' });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // 发布文档
  const handlePublish = async (doc: KnowledgeDocument) => {
    if (!selectedKB) return;
    try {
      setPublishingDocId(doc.id);
      await publishDocument(selectedKB.id, doc.id);
      showToast({ title: '文档已发布', variant: 'success' });
      const docs = await listDocuments(selectedKB.id);
      setDocuments(docs);
      if (selectedDoc && selectedDoc.id === doc.id) {
        const detail = await getKnowledgeDocument(selectedKB.id, doc.id);
        setSelectedDoc(detail);
      }
    } catch (err) {
      showToast({ title: getErrorMessage(err, '发布失败'), variant: 'error' });
    } finally {
      setPublishingDocId(null);
    }
  };

  // 取消发布文档（执行，确认弹窗回调后调用）
  const performUnpublish = async (doc: KnowledgeDocument) => {
    if (!selectedKB) return;
    try {
      setPublishingDocId(doc.id);
      await unpublishDocument(selectedKB.id, doc.id);
      showToast({ title: '文档已取消发布', variant: 'success' });
      const docs = await listDocuments(selectedKB.id);
      setDocuments(docs);
      if (selectedDoc && selectedDoc.id === doc.id) {
        const detail = await getKnowledgeDocument(selectedKB.id, doc.id);
        setSelectedDoc(detail);
      }
    } catch (err) {
      showToast({ title: getErrorMessage(err, '取消发布失败'), variant: 'error' });
    } finally {
      setPublishingDocId(null);
    }
  };

  // 删除文档（执行，确认弹窗回调后调用）
  const performDeleteDoc = async (doc: KnowledgeDocument) => {
    if (!selectedKB) return;
    try {
      setDeletingDocId(doc.id);
      await deleteDocument(selectedKB.id, doc.id);
      showToast({ title: '文档已删除', variant: 'success' });
      if (selectedDoc && selectedDoc.id === doc.id) {
        setSelectedDoc(null);
      }
      const docs = await listDocuments(selectedKB.id);
      setDocuments(docs);
      fetchKBs();
    } catch (err) {
      showToast({ title: getErrorMessage(err, '文档删除失败'), variant: 'error' });
    } finally {
      setDeletingDocId(null);
    }
  };

  // 删除知识库（执行，确认弹窗回调后调用）
  const performDeleteKB = async (kb: KnowledgeBase) => {
    try {
      setDeletingKbId(kb.id);
      await deleteKnowledgeBase(kb.id);
      showToast({ title: '知识库已删除', variant: 'success' });
      fetchKBs();
    } catch (err) {
      showToast({ title: getErrorMessage(err, '知识库删除失败'), variant: 'error' });
    } finally {
      setDeletingKbId(null);
    }
  };

  // ---- 确认弹窗（统一替代 window.confirm） ----
  const unpublishDialog = (
    <ConfirmDialog
      open={pendingUnpublish !== null}
      onClose={() => setPendingUnpublish(null)}
      onConfirm={() => {
        const doc = pendingUnpublish;
        setPendingUnpublish(null);
        if (doc) performUnpublish(doc);
      }}
      title="确认取消发布"
      message={
        pendingUnpublish
          ? `确定取消发布文档「${pendingUnpublish.title}」？取消后内容将不再被 AI 检索。`
          : undefined
      }
      danger={false}
      loading={publishingDocId !== null}
    />
  );

  const deleteDocDialog = (
    <ConfirmDialog
      open={pendingDeleteDoc !== null}
      onClose={() => setPendingDeleteDoc(null)}
      onConfirm={() => {
        const doc = pendingDeleteDoc;
        setPendingDeleteDoc(null);
        if (doc) performDeleteDoc(doc);
      }}
      title="删除文档"
      message={
        pendingDeleteDoc ? `确定删除文档「${pendingDeleteDoc.title}」？此操作不可恢复。` : undefined
      }
      loading={deletingDocId !== null}
    />
  );

  const deleteKBDialog = (
    <ConfirmDialog
      open={pendingDeleteKB !== null}
      onClose={() => setPendingDeleteKB(null)}
      onConfirm={() => {
        const kb = pendingDeleteKB;
        setPendingDeleteKB(null);
        if (kb) performDeleteKB(kb);
      }}
      title="删除知识库"
      message={
        pendingDeleteKB ? `确定删除知识库「${pendingDeleteKB.name}」及其所有文档？此操作不可恢复。` : undefined
      }
      loading={deletingKbId !== null}
    />
  );

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (iso: string | null | undefined) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('zh-CN', { hour12: false });
  };

  // ---- 文档详情视图 ----
  if (selectedKB && selectedDoc) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBackFromDoc}
            className="flex items-center gap-2 text-sm text-muted hover:text-text transition-colors cursor-pointer"
          >
            ← 返回文档列表
          </button>
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-semibold text-text truncate">{selectedDoc.title}</h2>
            <p className="text-sm text-muted mt-1">知识库：{selectedKB.name}</p>
          </div>
          <Badge variant={STATUS_VARIANTS[selectedDoc.status] || 'default'}>
            {STATUS_LABELS[selectedDoc.status] || selectedDoc.status}
          </Badge>
        </div>

        {docLoading ? (
          <LoadingSpinner text="加载中..." />
        ) : (
          <Card padding="lg" className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted">文件名</p>
                <p className="font-medium text-text mt-0.5">{selectedDoc.file_name || '—'}</p>
              </div>
              <div>
                <p className="text-muted">文件类型</p>
                <p className="font-medium text-text mt-0.5">{selectedDoc.file_type.toUpperCase()}</p>
              </div>
              <div>
                <p className="text-muted">文件大小</p>
                <p className="font-medium text-text mt-0.5">{formatFileSize(selectedDoc.file_size)}</p>
              </div>
              <div>
                <p className="text-muted">知识块数</p>
                <p className="font-medium text-text mt-0.5">{selectedDoc.chunk_count}</p>
              </div>
              <div>
                <p className="text-muted">发布时间</p>
                <p className="font-medium text-text mt-0.5">{formatDate(selectedDoc.published_at)}</p>
              </div>
              <div>
                <p className="text-muted">创建时间</p>
                <p className="font-medium text-text mt-0.5">{formatDate(selectedDoc.created_at)}</p>
              </div>
            </div>
            {selectedDoc.parse_error && (
              <div className="p-3 bg-error/10 border border-error/20 rounded-lg text-sm text-error">
                解析错误：{selectedDoc.parse_error}
              </div>
            )}
            <div className="flex gap-3 pt-2">
              {selectedDoc.status === 'published' ? (
                <Button
                  size="sm"
                  variant="ghost"
                  loading={publishingDocId === selectedDoc.id}
                  disabled={publishingDocId === selectedDoc.id}
                  onClick={() => setPendingUnpublish(selectedDoc)}
                >
                  取消发布
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="primary"
                  loading={publishingDocId === selectedDoc.id}
                  disabled={publishingDocId === selectedDoc.id}
                  onClick={() => handlePublish(selectedDoc)}
                >
                  发布
                </Button>
              )}
              <Button
                size="sm"
                variant="danger"
                loading={deletingDocId === selectedDoc.id}
                disabled={deletingDocId === selectedDoc.id}
                onClick={() => setPendingDeleteDoc(selectedDoc)}
              >
                删除
              </Button>
            </div>
          </Card>
        )}

        {unpublishDialog}
        {deleteDocDialog}
      </div>
    );
  }

  // ---- 知识库详情视图 ----
  if (selectedKB) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-sm text-muted hover:text-text transition-colors cursor-pointer"
          >
            ← 返回列表
          </button>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-text">{selectedKB.name}</h2>
            <p className="text-sm text-muted mt-1">{selectedKB.description}</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={STATUS_VARIANTS[selectedKB.status] || 'default'}>
              {STATUS_LABELS[selectedKB.status] || selectedKB.status}
            </Badge>
            <span className="text-sm text-muted">
              {selectedKB.document_count} 文档 · {selectedKB.total_chunks} 分块
            </span>
            <button
              onClick={() => openEditForm(selectedKB)}
              className="text-sm text-accent hover:text-accent-hover transition-colors cursor-pointer"
            >
              编辑
            </button>
          </div>
        </div>

        {/* Upload bar */}
        <div className="flex items-center gap-3 p-4 bg-surface rounded-lg border border-dashed border-border">
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.json,.pdf,.docx"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
          <Button
            size="sm"
            variant="primary"
            loading={uploading}
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {!uploading && <Upload className="h-4 w-4" aria-hidden="true" />}
            {uploading ? '上传中...' : '上传文档'}
          </Button>
          <span className="text-sm text-muted">支持 TXT、Markdown、JSON、PDF 格式</span>
        </div>

        {/* Document list */}
        <div className="space-y-3">
          {documents.length === 0 ? (
            <EmptyState
              icon={<FileText aria-hidden="true" className="h-5 w-5 text-muted" />}
              title="暂无文档"
              description="上传文档后，系统将自动解析并生成知识块"
            />
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 bg-card rounded-xl border border-border hover:border-accent/30 hover:shadow-sm transition-all"
              >
                <button
                  className="flex items-center gap-4 text-left flex-1 min-w-0 cursor-pointer"
                  onClick={() => handleSelectDoc(doc)}
                >
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center text-xs font-medium shrink-0 ${
                      FILE_TYPE_STYLES[doc.file_type] || FILE_TYPE_FALLBACK_STYLE
                    }`}
                  >
                    {doc.file_type.toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-text truncate">{doc.title}</p>
                    <p className="text-sm text-muted mt-0.5">
                      {doc.file_name} · {formatFileSize(doc.file_size)} · {doc.chunk_count} 个知识块
                    </p>
                  </div>
                </button>
                <div className="flex items-center gap-3 shrink-0">
                  <Badge variant={STATUS_VARIANTS[doc.status] || 'default'}>
                    {STATUS_LABELS[doc.status] || doc.status}
                  </Badge>
                  {doc.status !== 'published' ? (
                    <Button
                      size="sm"
                      variant="primary"
                      loading={publishingDocId === doc.id}
                      disabled={publishingDocId === doc.id}
                      onClick={() => handlePublish(doc)}
                    >
                      发布
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={publishingDocId === doc.id}
                      disabled={publishingDocId === doc.id}
                      onClick={() => setPendingUnpublish(doc)}
                    >
                      取消发布
                    </Button>
                  )}
                  <button
                    onClick={() => setPendingDeleteDoc(doc)}
                    className="cursor-pointer transition-colors text-sm text-muted hover:text-error disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {deletingDocId === doc.id ? '删除中...' : '删除'}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {unpublishDialog}
        {deleteDocDialog}
      </div>
    );
  }

  // ---- 知识库列表视图 ----
  return (
    <div className="space-y-6">
      <PageHeader
        title="知识库管理"
        description="管理保险产品知识文档，为 AI 助手提供专业知识支撑"
        actions={
          <>
            {isDemoEnv && <Badge variant="warning">演示模式</Badge>}
            <Button variant="primary" onClick={openCreateForm}>
              + 新建知识库
            </Button>
          </>
        }
      />

      {/* Create / Edit form */}
      {showCreateForm && (
        <Card padding="lg" className="space-y-4">
          <CardTitle>{editingKB ? '编辑知识库' : '新建知识库'}</CardTitle>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="名称 *"
              type="text"
              value={newKB.name}
              onChange={(e) => setNewKB({ ...newKB, name: e.target.value })}
              placeholder="如：华安保险产品知识库"
              maxLength={200}
            />
            <Select
              label="分类"
              value={newKB.category}
              onChange={(e) => setNewKB({ ...newKB, category: e.target.value })}
            >
              <option value="product">产品知识</option>
              <option value="regulation">监管合规</option>
              <option value="training">培训资料</option>
              <option value="faq">常见问题</option>
            </Select>
          </div>
          <Textarea
            label="描述"
            value={newKB.description}
            onChange={(e) => setNewKB({ ...newKB, description: e.target.value })}
            placeholder="简要描述知识库的用途和内容范围"
            rows={2}
            maxLength={2000}
          />
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-text cursor-pointer">
              <input
                type="checkbox"
                checked={newKB.is_public}
                onChange={(e) => setNewKB({ ...newKB, is_public: e.target.checked })}
                className="rounded border-border accent-accent"
              />
              公开可见（全员可访问）
            </label>
          </div>
          <div className="flex gap-3">
            {editingKB ? (
              <Button variant="primary" onClick={handleUpdate} loading={savingKB}>
                保存修改
              </Button>
            ) : (
              <Button variant="primary" onClick={handleCreate} loading={creating}>
                创建
              </Button>
            )}
            <Button
              variant="ghost"
              onClick={() => {
                setShowCreateForm(false);
                setEditingKB(null);
              }}
            >
              取消
            </Button>
          </div>
        </Card>
      )}

      {/* KB Cards */}
      {loading ? (
        <LoadingSpinner text="加载中..." />
      ) : knowledgeBases.length === 0 ? (
        <EmptyState
          icon={<LibraryBig aria-hidden="true" className="h-5 w-5 text-muted" />}
          title="暂无知识库"
          description="创建知识库并上传文档，为 AI 助手提供专业知识"
          action={
            <Button variant="secondary" size="sm" onClick={openCreateForm}>
              新建知识库
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {knowledgeBases.map((kb) => (
            <div
              key={kb.id}
              className="p-5 bg-card rounded-xl border border-border hover:border-accent/30 hover:shadow-md transition-all cursor-pointer group"
              onClick={() => handleSelectKB(kb)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Badge variant="primary">{CATEGORY_LABELS[kb.category] || kb.category}</Badge>
                  <Badge variant={STATUS_VARIANTS[kb.status] || 'default'}>
                    {STATUS_LABELS[kb.status] || kb.status}
                  </Badge>
                </div>
              </div>
              <h3 className="font-semibold text-text group-hover:text-accent transition-colors">
                {kb.name}
              </h3>
              <p className="text-sm text-muted mt-1 line-clamp-2">{kb.description}</p>
              <div className="flex items-center gap-4 mt-4 pt-3 border-t border-border">
                <span className="text-sm text-muted">{kb.document_count} 文档</span>
                <span className="text-sm text-muted">{kb.total_chunks} 分块</span>
                <span className="text-sm text-muted">v{kb.version}</span>
              </div>
              <div className="flex gap-3 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    openEditForm(kb);
                  }}
                  className="text-xs text-accent hover:text-accent-hover transition-colors cursor-pointer"
                >
                  编辑
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setPendingDeleteKB(kb);
                  }}
                  disabled={deletingKbId === kb.id}
                  className="text-xs text-error/80 hover:text-error transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {deletingKbId === kb.id ? '删除中...' : '删除'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {deleteKBDialog}
    </div>
  );
}
