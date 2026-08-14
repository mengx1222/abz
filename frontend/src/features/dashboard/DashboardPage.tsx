import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { useNavigate } from 'react-router-dom';

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 6) return '凌晨好';
  if (hour < 9) return '早上好';
  if (hour < 12) return '上午好';
  if (hour < 14) return '中午好';
  if (hour < 17) return '下午好';
  if (hour < 19) return '傍晚好';
  return '晚上好';
}

const quickActions = [
  { label: '问产品', icon: '🤖', path: '/product-qa', color: 'bg-accent/10 text-accent' },
  { label: '分析客户', icon: '👥', path: '/customers', color: 'bg-success/10 text-success' },
  { label: '生成话术', icon: '💬', path: '/scripts', color: 'bg-warning/10 text-warning' },
  { label: '开始陪练', icon: '🎯', path: '/training', color: 'bg-error/10 text-error' },
];

const todayStats = [
  { label: '今日通话', value: '12', sub: '+3 较昨日', trend: 'up' as const },
  { label: '成交保单', value: '2', sub: '+1 较昨日', trend: 'up' as const },
  { label: '待跟进客户', value: '8', sub: '3个高意向', trend: 'neutral' as const },
  { label: 'AI 问答次数', value: '34', sub: '产品 18 · 话术 16', trend: 'neutral' as const },
];

const aiSuggestions = [
  {
    title: '王女士的续保即将到期',
    desc: '客户重疾险将于30天后到期，建议本周内联系续保，可推荐升级方案。',
    tag: '紧急跟进',
    tagVariant: 'error' as const,
  },
  {
    title: '李先生对医疗险有兴趣',
    desc: '上周咨询过百万医疗险，AI分析其家庭情况推荐了家庭版方案，建议今日回访。',
    tag: '高意向',
    tagVariant: 'warning' as const,
  },
  {
    title: '新版重疾险产品培训',
    desc: '公司刚发布了新版重疾险产品，建议花10分钟了解核心卖点变化。',
    tag: '学习',
    tagVariant: 'default' as const,
  },
];

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-text">
          {getGreeting()}，{user?.name || '用户'}
        </h1>
        <p className="text-muted text-sm mt-1">
          {user?.role_name || '代理人'} · 今天是{new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {quickActions.map((action) => (
          <button
            key={action.path}
            onClick={() => navigate(action.path)}
            className="bg-card border border-border rounded-xl p-4 hover:shadow-md transition-all duration-200 cursor-pointer text-left group"
          >
            <span className="text-2xl block mb-2">{action.icon}</span>
            <p className="text-sm font-medium text-text group-hover:text-accent transition-colors">
              {action.label}
            </p>
          </button>
        ))}
      </div>

      {/* Today Stats */}
      <div>
        <h2 className="text-base font-semibold text-text mb-3">今日工作</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {todayStats.map((stat) => (
            <Card key={stat.label} padding="md">
              <p className="text-sm text-muted">{stat.label}</p>
              <p className="text-2xl font-bold text-text mt-1">{stat.value}</p>
              <p className="text-xs text-muted mt-1">{stat.sub}</p>
            </Card>
          ))}
        </div>
      </div>

      {/* AI Suggestions */}
      <div>
        <h2 className="text-base font-semibold text-text mb-3">AI 今日建议</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {aiSuggestions.map((s) => (
            <Card key={s.title} padding="md" hover>
              <div className="flex items-start justify-between mb-2">
                <CardTitle className="text-sm leading-snug">{s.title}</CardTitle>
                <Badge variant={s.tagVariant}>{s.tag}</Badge>
              </div>
              <CardDescription className="text-xs leading-relaxed">{s.desc}</CardDescription>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
