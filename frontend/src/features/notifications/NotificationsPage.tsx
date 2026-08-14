import { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

type NotificationType = 'system' | 'followup' | 'training' | 'team';

interface DemoNotification {
  id: string;
  type: NotificationType;
  title: string;
  content: string;
  time: string;
  read: boolean;
}

const typeLabels: Record<NotificationType, { label: string; variant: 'default' | 'warning' | 'error' | 'success' }> = {
  system: { label: '系统通知', variant: 'default' },
  followup: { label: '客户跟进', variant: 'warning' },
  training: { label: '训练提醒', variant: 'success' },
  team: { label: '团队动态', variant: 'default' },
};

const typeFilters: { key: NotificationType | 'all'; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'followup', label: '客户跟进' },
  { key: 'system', label: '系统通知' },
  { key: 'training', label: '训练提醒' },
  { key: 'team', label: '团队动态' },
];

const demoNotifications: DemoNotification[] = [
  {
    id: '1',
    type: 'followup',
    title: '王丽华的续保即将到期',
    content: '客户重疾险将于30天后到期，建议本周内联系续保。AI已生成续保话术，点击查看。',
    time: '10分钟前',
    read: false,
  },
  {
    id: '2',
    type: 'system',
    title: '新版重疾险产品上线',
    content: '公司发布了2025版重疾险产品，新增特定疾病额外赔付和心脑血管二次赔付。请尽快完成产品学习。',
    time: '1小时前',
    read: false,
  },
  {
    id: '3',
    type: 'training',
    title: '恭喜完成「电销开场白训练」',
    content: '您在本次训练中获得了92分的高分！AI建议：开场节奏把控优秀，可以尝试增加更多互动提问。',
    time: '2小时前',
    read: false,
  },
  {
    id: '4',
    type: 'followup',
    title: '李建国待回访提醒',
    content: '上周咨询过百万医疗险，AI分析其家庭情况推荐了家庭版方案，建议今日完成回访跟进。',
    time: '3小时前',
    read: true,
  },
  {
    id: '5',
    type: 'team',
    title: '张主管发布了本周销售目标',
    content: '本周团队目标：人均通话50通，保单3件。请各位合理安排时间，加油冲刺！',
    time: '5小时前',
    read: true,
  },
  {
    id: '6',
    type: 'system',
    title: '系统维护通知',
    content: '系统将于本周六凌晨2:00-4:00进行例行维护升级，届时部分功能可能暂时不可用。',
    time: '1天前',
    read: true,
  },
  {
    id: '7',
    type: 'training',
    title: '新的训练任务已分配',
    content: '根据您的能力评估结果，AI为您推荐了「异议处理：保费太贵」训练场景，建议本周完成。',
    time: '1天前',
    read: true,
  },
  {
    id: '8',
    type: 'team',
    title: '陈明辉在社区发布新帖',
    content: '陈明辉分享了「如何应对客户比价」的实战经验，已获得234个点赞，快去看看吧。',
    time: '2天前',
    read: true,
  },
];

export function NotificationsPage() {
  const user = useAuthStore((s) => s.user);
  const [filter, setFilter] = useState<NotificationType | 'all'>('all');

  const filtered =
    filter === 'all'
      ? demoNotifications
      : demoNotifications.filter((n) => n.type === filter);

  const unreadCount = demoNotifications.filter((n) => !n.read).length;

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">消息中心</h1>
            <Badge variant="warning">演示模式</Badge>
            {unreadCount > 0 && <Badge variant="error">{unreadCount} 条未读</Badge>}
          </div>
          <p className="text-muted text-sm mt-1">
            {user?.name || '用户'}，查看系统通知、团队消息和AI提醒
          </p>
        </div>
        <Button variant="secondary" size="sm" disabled>
          全部已读
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {typeFilters.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === f.key
                ? 'bg-accent text-white'
                : 'bg-card border border-border text-muted hover:text-text'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Notification List */}
      <div className="space-y-2">
        {filtered.map((notification) => {
          const typeInfo = typeLabels[notification.type];
          return (
            <Card
              key={notification.id}
              padding="md"
              hover
              className={!notification.read ? 'border-l-2 border-l-accent' : ''}
            >
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${notification.read ? 'bg-transparent' : 'bg-accent'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CardTitle className={`text-sm ${notification.read ? 'font-medium' : 'font-semibold'}`}>
                      {notification.title}
                    </CardTitle>
                    <Badge variant={typeInfo.variant}>{typeInfo.label}</Badge>
                  </div>
                  <CardDescription className="mt-1 text-xs leading-relaxed">
                    {notification.content}
                  </CardDescription>
                  <p className="text-xs text-muted/60 mt-1.5">{notification.time}</p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <Card padding="lg">
          <div className="text-center py-8 text-muted text-sm">暂无该类型的通知</div>
        </Card>
      )}

      <p className="text-xs text-muted text-center">演示模式 — 功能待开发 · 当前展示为示例数据</p>
    </div>
  );
}
