import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { useToast } from '../../hooks/useToast';
import {
  listCustomers,
  createCustomer,
  deleteCustomer,
  type Customer,
  type CustomerCreate,
} from '../../services/customerService';

// ----------- Constants -----------

const STAGE_MAP: Record<
  string,
  { label: string; variant: 'default' | 'warning' | 'success' | 'error' }
> = {
  initial_contact: { label: '初步接触', variant: 'default' },
  needs_analysis: { label: '需求分析', variant: 'default' },
  proposal: { label: '方案推荐', variant: 'warning' },
  presentation: { label: '方案展示', variant: 'warning' },
  negotiation: { label: '谈判中', variant: 'warning' },
  closed_won: { label: '已签单', variant: 'success' },
  closed_lost: { label: '已流失', variant: 'error' },
};

const TYPE_MAP: Record<string, string> = {
  prospective: '准客户',
  active: '活跃客户',
  lapsed: '流失客户',
};

const STAGE_OPTIONS = Object.entries(STAGE_MAP);
const INTENTION_OPTIONS = [1, 2, 3, 4, 5];

// ----------- Helpers -----------

function maskPhone(phone: string | null): string {
  if (!phone || phone.length < 7) return phone ?? '-';
  return phone.slice(0, 3) + '****' + phone.slice(-4);
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

function StarRating({ level }: { level: number }) {
  return (
    <span className="inline-flex gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <svg
          key={i}
          className={`w-4 h-4 ${i < level ? 'text-warning' : 'text-border'}`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ))}
    </span>
  );
}

// ----------- Create Modal -----------

interface CreateForm {
  name: string;
  age: string;
  gender: string;
  phone: string;
  customer_type: string;
  insurance_type: string;
  current_stage: string;
  intention_level: string;
  source_channel: string;
  tags: string;
  notes: string;
}

const EMPTY_FORM: CreateForm = {
  name: '',
  age: '',
  gender: '',
  phone: '',
  customer_type: 'prospective',
  insurance_type: '',
  current_stage: 'initial_contact',
  intention_level: '3',
  source_channel: '',
  tags: '',
  notes: '',
};

function CreateCustomerModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const { toast } = useToast();
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const update = (key: keyof CreateForm, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      toast({ title: '请输入客户姓名', variant: 'warning' });
      return;
    }
    setSubmitting(true);
    try {
      const payload: CustomerCreate = {
        name: form.name.trim(),
        age: form.age ? Number(form.age) : null,
        gender: form.gender ? (form.gender as 'male' | 'female') : null,
        phone: form.phone.trim() || null,
        customer_type: form.customer_type as CustomerCreate['customer_type'],
        insurance_type: form.insurance_type.trim() || null,
        current_stage: form.current_stage || undefined,
        intention_level: form.intention_level
          ? Number(form.intention_level)
          : undefined,
        source_channel: form.source_channel.trim() || null,
        tags: form.tags.trim()
          ? form.tags
              .split(/[,，]/)
              .map((t) => t.trim())
              .filter(Boolean)
          : null,
        notes: form.notes.trim() || null,
      };
      await createCustomer(payload);
      toast({ title: '客户创建成功', variant: 'success' });
      setForm(EMPTY_FORM);
      onCreated();
      onClose();
    } catch {
      toast({ title: '创建失败，请重试', variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  const fieldClass =
    'w-full h-10 rounded-lg border border-border bg-white px-3 text-sm text-text placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent';
  const selectClass = fieldClass;
  const labelClass = 'text-sm font-medium text-text mb-1.5 block';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      {/* Dialog */}
      <div className="relative bg-card rounded-xl border border-border shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-text">新增客户</h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-text text-xl leading-none cursor-pointer"
          >
            x
          </button>
        </div>

        <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>
              姓名 <span className="text-error">*</span>
            </label>
            <input
              className={fieldClass}
              value={form.name}
              onChange={(e) => update('name', e.target.value)}
              placeholder="请输入姓名"
            />
          </div>
          <div>
            <label className={labelClass}>年龄</label>
            <input
              type="number"
              min={0}
              max={150}
              className={fieldClass}
              value={form.age}
              onChange={(e) => update('age', e.target.value)}
              placeholder="请输入年龄"
            />
          </div>
          <div>
            <label className={labelClass}>性别</label>
            <select
              className={selectClass}
              value={form.gender}
              onChange={(e) => update('gender', e.target.value)}
            >
              <option value="">请选择</option>
              <option value="male">男</option>
              <option value="female">女</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>手机号</label>
            <input
              className={fieldClass}
              value={form.phone}
              onChange={(e) => update('phone', e.target.value)}
              placeholder="请输入手机号"
            />
          </div>
          <div>
            <label className={labelClass}>客户类型</label>
            <select
              className={selectClass}
              value={form.customer_type}
              onChange={(e) => update('customer_type', e.target.value)}
            >
              {Object.entries(TYPE_MAP).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>感兴趣险种</label>
            <input
              className={fieldClass}
              value={form.insurance_type}
              onChange={(e) => update('insurance_type', e.target.value)}
              placeholder="如: 重疾险、医疗险"
            />
          </div>
          <div>
            <label className={labelClass}>当前阶段</label>
            <select
              className={selectClass}
              value={form.current_stage}
              onChange={(e) => update('current_stage', e.target.value)}
            >
              {STAGE_OPTIONS.map(([k, v]) => (
                <option key={k} value={k}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>意向等级 (1-5)</label>
            <select
              className={selectClass}
              value={form.intention_level}
              onChange={(e) => update('intention_level', e.target.value)}
            >
              {INTENTION_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>来源渠道</label>
            <input
              className={fieldClass}
              value={form.source_channel}
              onChange={(e) => update('source_channel', e.target.value)}
              placeholder="如: 转介绍、线上咨询"
            />
          </div>
          <div>
            <label className={labelClass}>标签 (逗号分隔)</label>
            <input
              className={fieldClass}
              value={form.tags}
              onChange={(e) => update('tags', e.target.value)}
              placeholder="如: 高净值, 有小孩"
            />
          </div>
          <div className="sm:col-span-2">
            <label className={labelClass}>备注</label>
            <textarea
              className={
                fieldClass + ' h-20 resize-none'
              }
              value={form.notes}
              onChange={(e) => update('notes', e.target.value)}
              placeholder="备注信息"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 p-4 border-t border-border">
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={submitting}>
            创建
          </Button>
        </div>
      </div>
    </div>
  );
}

// ----------- Filter Pills -----------

const TYPE_FILTERS = [
  { key: '', label: '全部' },
  { key: 'prospective', label: '准客户' },
  { key: 'active', label: '活跃' },
  { key: 'lapsed', label: '流失' },
];

// ----------- Main Page -----------

export function CustomersPage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  // Filters
  const [search, setSearch] = useState('');
  const [customerType, setCustomerType] = useState('');
  const [stageFilter, setStageFilter] = useState('');
  const [intentionFilter, setIntentionFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Data
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create modal
  const [showCreate, setShowCreate] = useState(false);

  // Delete
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listCustomers({
        search: search || undefined,
        customer_type: customerType || undefined,
        current_stage: stageFilter || undefined,
        intention_level: intentionFilter ? Number(intentionFilter) : undefined,
        page,
        page_size: pageSize,
      });
      setCustomers(result.items);
      setTotal(result.total);
      setTotalPages(result.totalPages);
    } catch {
      setError('加载客户列表失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [search, customerType, stageFilter, intentionFilter, page]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [search, customerType, stageFilter, intentionFilter]);

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`确定要删除客户 "${name}" 吗？`)) return;
    setDeletingId(id);
    try {
      await deleteCustomer(id);
      toast({ title: '已删除', variant: 'success' });
      fetchCustomers();
    } catch {
      toast({ title: '删除失败', variant: 'error' });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">客户360</h1>
            <Badge variant="warning">演示模式</Badge>
          </div>
          <p className="text-muted text-sm mt-1">
            共 {total} 位客户 · AI驱动客户洞察与需求分析
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => setShowCreate(true)}
        >
          + 新增客户
        </Button>
      </div>

      {/* Search & Filters */}
      <Card padding="md">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col sm:flex-row gap-3">
            <Input
              placeholder="搜索客户姓名或手机号..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="sm:w-64"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Type filter pills */}
            {TYPE_FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setCustomerType(f.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  customerType === f.key
                    ? 'bg-accent text-white'
                    : 'bg-bg text-muted hover:text-text'
                }`}
              >
                {f.label}
              </button>
            ))}

            <span className="text-border mx-1">|</span>

            {/* Stage dropdown */}
            <select
              value={stageFilter}
              onChange={(e) => setStageFilter(e.target.value)}
              className="h-8 rounded-lg border border-border bg-white px-2 text-xs text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              <option value="">全部阶段</option>
              {STAGE_OPTIONS.map(([k, v]) => (
                <option key={k} value={k}>
                  {v.label}
                </option>
              ))}
            </select>

            {/* Intention dropdown */}
            <select
              value={intentionFilter}
              onChange={(e) => setIntentionFilter(e.target.value)}
              className="h-8 rounded-lg border border-border bg-white px-2 text-xs text-text focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              <option value="">全部意向</option>
              {INTENTION_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  意向等级 {n}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Customer Table */}
      <Card padding="none">
        {loading ? (
          <div className="py-16">
            <LoadingSpinner text="加载客户列表..." />
          </div>
        ) : error ? (
          <div className="py-16 text-center">
            <p className="text-error text-sm mb-3">{error}</p>
            <Button variant="secondary" size="sm" onClick={fetchCustomers}>
              重新加载
            </Button>
          </div>
        ) : customers.length === 0 ? (
          <div className="py-16 text-center text-muted text-sm">
            未找到匹配的客户
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 font-medium text-muted">
                    姓名
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted">
                    手机号
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted">
                    险种
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted">
                    标签
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted">
                    阶段
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted">
                    意向度
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted">
                    来源
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-muted">
                    最近更新
                  </th>
                  <th className="text-right px-4 py-3 font-medium text-muted">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => {
                  const stage = STAGE_MAP[c.current_stage];
                  return (
                    <tr
                      key={c.id}
                      className="border-b border-border last:border-b-0 hover:bg-bg/50 transition-colors cursor-pointer"
                      onClick={() => navigate(`/customers/${c.id}`)}
                    >
                      <td className="px-4 py-3 font-medium text-text">
                        {c.name}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {maskPhone(c.phone)}
                      </td>
                      <td className="px-4 py-3 text-text">
                        {c.insurance_type || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1 flex-wrap">
                          {c.tags && c.tags.length > 0
                            ? c.tags.map((tag) => (
                                <Badge key={tag} variant="default">
                                  {tag}
                                </Badge>
                              ))
                            : '-'}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {stage ? (
                          <Badge variant={stage.variant}>{stage.label}</Badge>
                        ) : (
                          c.current_stage
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <StarRating level={c.intention_level} />
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {c.source_channel || '-'}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {formatDate(c.updated_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/customers/${c.id}`);
                          }}
                        >
                          查看
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(c.id, c.name);
                          }}
                          loading={deletingId === c.id}
                          className="text-error hover:text-error"
                        >
                          删除
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            上一页
          </Button>
          <span className="text-sm text-muted">
            {page} / {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </Button>
        </div>
      )}

      {/* Create Modal */}
      <CreateCustomerModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={fetchCustomers}
      />
    </div>
  );
}


