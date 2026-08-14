import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';

const monthlyStats = [
  { label: '本月通话量', value: '186', unit: '通', change: '+12%', up: true },
  { label: '转化率', value: '14.2', unit: '%', change: '+2.3%', up: true },
  { label: '成交保单', value: '26', unit: '件', change: '+5', up: true },
  { label: '保费收入', value: '12.8', unit: '万', change: '+3.2万', up: true },
];

const weeklyTrend = [
  { day: '周一', calls: 32, deals: 3 },
  { day: '周二', calls: 28, deals: 5 },
  { day: '周三', calls: 35, deals: 4 },
  { day: '周四', calls: 30, deals: 2 },
  { day: '周五', calls: 38, deals: 6 },
  { day: '周六', calls: 15, deals: 4 },
  { day: '周日', calls: 8, deals: 2 },
];

const maxCalls = Math.max(...weeklyTrend.map((d) => d.calls));

const abilityRadar = [
  { label: '产品知识', score: 82 },
  { label: '沟通技巧', score: 75 },
  { label: '异议处理', score: 68 },
  { label: '需求分析', score: 88 },
  { label: '促成能力', score: 60 },
  { label: '客户维护', score: 72 },
];

const learningCourses = [
  { title: '重疾险产品知识进阶', progress: 85, total: '12/14 课', status: '进行中' as const },
  { title: '电销黄金开场白技巧', progress: 100, total: '8/8 课', status: '已完成' as const },
  { title: '高净值客户经营方法', progress: 40, total: '4/10 课', status: '进行中' as const },
  { title: '保险法规与合规销售', progress: 100, total: '6/6 课', status: '已完成' as const },
];

const statusVariant = { '进行中': 'warning' as const, '已完成': 'success' as const };

export function GrowthPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-text">我的成长</h1>
          <Badge variant="warning">演示模式</Badge>
        </div>
        <p className="text-muted text-sm mt-1">
          {user?.name || '用户'}，追踪个人成长轨迹，AI定制学习路径
        </p>
      </div>

      {/* Monthly Performance Stats */}
      <div>
        <h2 className="text-base font-semibold text-text mb-3">本月业绩</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {monthlyStats.map((stat) => (
            <Card key={stat.label} padding="md">
              <p className="text-sm text-muted">{stat.label}</p>
              <div className="flex items-baseline gap-1 mt-1">
                <p className="text-2xl font-bold text-text">{stat.value}</p>
                <p className="text-sm text-muted">{stat.unit}</p>
              </div>
              <p className={`text-xs mt-1 ${stat.up ? 'text-success' : 'text-error'}`}>
                {stat.up ? '↑' : '↓'} {stat.change} 较上月
              </p>
            </Card>
          ))}
        </div>
      </div>

      {/* Weekly Trend */}
      <Card padding="md">
        <CardHeader>
          <CardTitle>本周通话趋势</CardTitle>
          <CardDescription>每日通话量与成交数对比</CardDescription>
        </CardHeader>
        <div className="flex items-end gap-2 h-32 mt-2">
          {weeklyTrend.map((day) => (
            <div key={day.day} className="flex-1 flex flex-col items-center gap-1">
              <div className="w-full flex gap-0.5 items-end justify-center" style={{ height: '100px' }}>
                <div
                  className="w-3/5 bg-accent/80 rounded-t-sm"
                  style={{ height: `${(day.calls / maxCalls) * 100}%` }}
                  title={`通话 ${day.calls}`}
                />
                <div
                  className="w-2/5 bg-success/80 rounded-t-sm"
                  style={{ height: `${(day.deals / maxCalls) * 100}%` }}
                  title={`成交 ${day.deals}`}
                />
              </div>
              <span className="text-xs text-muted">{day.day}</span>
            </div>
          ))}
        </div>
        <div className="flex gap-4 mt-3 text-xs text-muted">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-accent/80 inline-block" /> 通话量</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-success/80 inline-block" /> 成交数</span>
        </div>
      </Card>

      {/* Two-column: Ability Radar + Learning Progress */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Ability Radar */}
        <Card padding="md">
          <CardHeader>
            <CardTitle>能力评估</CardTitle>
            <CardDescription>AI综合评估您的专业能力</CardDescription>
          </CardHeader>
          <div className="space-y-3 mt-2">
            {abilityRadar.map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-text">{item.label}</span>
                  <span className="text-muted">{item.score}分</span>
                </div>
                <div className="h-2 bg-bg rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      item.score >= 80 ? 'bg-success' : item.score >= 65 ? 'bg-warning' : 'bg-error'
                    }`}
                    style={{ width: `${item.score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Learning Progress */}
        <Card padding="md">
          <CardHeader>
            <CardTitle>学习进度</CardTitle>
            <CardDescription>AI推荐的学习课程</CardDescription>
          </CardHeader>
          <div className="space-y-3 mt-2">
            {learningCourses.map((course) => (
              <div key={course.title}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-text truncate mr-2">{course.title}</span>
                  <Badge variant={statusVariant[course.status]}>{course.status}</Badge>
                </div>
                <div className="h-2 bg-bg rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${course.progress === 100 ? 'bg-success' : 'bg-accent'}`}
                    style={{ width: `${course.progress}%` }}
                  />
                </div>
                <p className="text-xs text-muted mt-1">{course.total}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <p className="text-xs text-muted text-center">演示模式 — 功能待开发 · 当前展示为示例数据</p>
    </div>
  );
}
