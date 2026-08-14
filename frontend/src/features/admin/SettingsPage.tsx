import { useState, useEffect } from 'react';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { cn } from '../../utils/cn';
import { settingsApi, type SystemSettings } from '../../services/adminService';

interface SettingField {
  key: string;
  label: string;
  type: 'string' | 'number' | 'boolean';
}

interface SettingSection {
  title: string;
  description: string;
  category: keyof SystemSettings;
  fields: SettingField[];
}

const sections: SettingSection[] = [
  {
    title: 'AI 设置',
    description: 'AI 模型与推理参数配置',
    category: 'ai',
    fields: [
      { key: 'default_model', label: '默认模型', type: 'string' },
      { key: 'max_tokens', label: '最大 Token 数', type: 'number' },
      { key: 'temperature', label: '温度参数', type: 'number' },
      { key: 'timeout_seconds', label: '超时时间（秒）', type: 'number' },
      { key: 'rate_limit_per_minute', label: '每分钟速率限制', type: 'number' },
    ],
  },
  {
    title: 'RAG 设置',
    description: '检索增强生成参数配置',
    category: 'rag',
    fields: [
      { key: 'embedding_model', label: '嵌入模型', type: 'string' },
      { key: 'default_chunk_size', label: '默认分块大小', type: 'number' },
      { key: 'default_chunk_overlap', label: '分块重叠长度', type: 'number' },
      { key: 'top_k', label: 'Top-K 检索数量', type: 'number' },
      { key: 'similarity_threshold', label: '相似度阈值', type: 'number' },
    ],
  },
  {
    title: '合规设置',
    description: '内容合规检查参数配置',
    category: 'compliance',
    fields: [
      { key: 'auto_check_enabled', label: '自动合规检查', type: 'boolean' },
      { key: 'severity_levels', label: '严重等级', type: 'string' },
      { key: 'auto_reject_violations', label: '自动拒绝违规内容', type: 'boolean' },
    ],
  },
  {
    title: '通知设置',
    description: '系统通知与提醒参数配置',
    category: 'notification',
    fields: [
      { key: 'follow_up_reminder_hours', label: '跟进提醒间隔（小时）', type: 'number' },
      { key: 'inactive_customer_days', label: '不活跃客户天数', type: 'number' },
    ],
  },
  {
    title: '社区设置',
    description: '社区功能参数配置',
    category: 'community',
    fields: [
      { key: 'post_review_enabled', label: '帖子审核', type: 'boolean' },
      { key: 'max_tags_per_post', label: '每帖最大标签数', type: 'number' },
      { key: 'comment_max_length', label: '评论最大长度', type: 'number' },
    ],
  },
];

function formatValue(value: unknown, type: SettingField['type']): string {
  if (value === undefined || value === null) return '未设置';
  if (type === 'boolean') {
    return value ? '是' : '否';
  }
  if (type === 'number') {
    return String(value);
  }
  return String(value);
}

function CollapsibleSection({
  section,
  data,
}: {
  section: SettingSection;
  data: Record<string, unknown> | undefined;
}) {
  const [open, setOpen] = useState(true);

  return (
    <Card padding="none" className="overflow-hidden">
      {/* Section Header - clickable to collapse */}
      <button
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-bg/50 transition-colors cursor-pointer"
        onClick={() => setOpen(!open)}
      >
        <div className="text-left">
          <CardTitle className="flex items-center gap-2">
            {section.title}
            <svg
              className={cn(
                'w-4 h-4 text-muted transition-transform duration-200',
                !open && '-rotate-90'
              )}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </CardTitle>
          <CardDescription>{section.description}</CardDescription>
        </div>
        <Button variant="ghost" size="sm" disabled>
          编辑
        </Button>
      </button>

      {/* Section Body */}
      {open && (
        <div className="border-t border-border">
          <div className="divide-y divide-border">
            {section.fields.map((field) => {
              const value = data?.[field.key];
              const displayValue = formatValue(value, field.type);

              return (
                <div key={field.key} className="flex items-center justify-between px-6 py-3">
                  <span className="text-sm text-muted">{field.label}</span>
                  <div className="flex items-center gap-2">
                    {field.type === 'boolean' ? (
                      <Badge
                        variant={value ? 'success' : 'default'}
                        className={cn(
                          value
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-500'
                        )}
                      >
                        {displayValue}
                      </Badge>
                    ) : (
                      <span
                        className={cn(
                          'text-sm font-medium',
                          value === undefined || value === null
                            ? 'text-muted'
                            : 'text-text'
                        )}
                      >
                        {displayValue}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}

export function SettingsPage() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    settingsApi
      .get()
      .then((res) => {
        if (!cancelled) setSettings(res.data.data);
      })
      .catch(() => {
        if (!cancelled) setError('加载系统设置失败，请重试');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text">系统设置</h1>
          <Badge className="bg-amber-100 text-amber-700">演示模式</Badge>
        </div>
        <LoadingSpinner size="lg" text="正在加载设置..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text">系统设置</h1>
          <Badge className="bg-amber-100 text-amber-700">演示模式</Badge>
        </div>
        <Card>
          <div className="text-center py-8 text-muted">{error}</div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">系统设置</h1>
          <p className="text-sm text-muted mt-1">查看和配置系统参数（演示模式下为只读）</p>
        </div>
        <Badge className="bg-amber-100 text-amber-700 w-fit">演示模式</Badge>
      </div>

      {/* Setting Sections */}
      <div className="space-y-4">
        {sections.map((section) => (
          <CollapsibleSection
            key={section.category}
            section={section}
            data={settings?.[section.category] as Record<string, unknown> | undefined}
          />
        ))}
      </div>
    </div>
  );
}
