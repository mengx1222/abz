import { useState, useEffect } from 'react';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { cn } from '../../utils/cn';
import {
  analyticsApi,
  type OverviewData,
  type AiUsageData,
  type TrainingAnalytics,
  type CommunityAnalytics,
} from '../../services/adminService';

type Period = 'week' | 'month' | 'quarter' | 'year';

const periodLabels: Record<Period, string> = {
  week: '周',
  month: '月',
  quarter: '季',
  year: '年',
};

const barColors = [
  'bg-accent',
  'bg-accent/80',
  'bg-accent/60',
  'bg-accent/40',
  'bg-accent/25',
  'bg-accent/15',
];

export function AnalyticsPage() {
  const [period, setPeriod] = useState<Period>('month');
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [aiUsage, setAiUsage] = useState<AiUsageData | null>(null);
  const [training, setTraining] = useState<TrainingAnalytics | null>(null);
  const [community, setCommunity] = useState<CommunityAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    Promise.all([
      analyticsApi.overview(period),
      analyticsApi.aiUsage(period),
      analyticsApi.training(period),
      analyticsApi.community(period),
    ])
      .then(([ov, ai, tr, co]) => {
        if (cancelled) return;
        setOverview(ov.data.data);
        setAiUsage(ai.data.data);
        setTraining(tr.data.data);
        setCommunity(co.data.data);
      })
      .catch(() => {
        if (!cancelled) setError('加载数据失败，请重试');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [period]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text">数据看板</h1>
          <Badge className="bg-amber-100 text-amber-700">演示模式</Badge>
        </div>
        <LoadingSpinner size="lg" text="正在加载数据..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text">数据看板</h1>
          <Badge className="bg-amber-100 text-amber-700">演示模式</Badge>
        </div>
        <Card>
          <div className="text-center py-8 text-muted">{error}</div>
        </Card>
      </div>
    );
  }

  const stats = overview?.user_stats;
  const aiStats = overview?.ai_stats;
  const trainStats = overview?.training_stats;
  const commStats = overview?.community_stats;

  const statCards = [
    {
      label: '总用户数',
      value: stats?.total_users ?? 0,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
      trend: `+${stats?.new_users ?? 0} 新增`,
      trendUp: true,
      color: 'text-accent bg-accent/10',
    },
    {
      label: '活跃率',
      value: `${((stats?.active_rate ?? 0) * 100).toFixed(1)}%`,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
      ),
      trend: `${stats?.active_users ?? 0} 活跃用户`,
      trendUp: true,
      color: 'text-success bg-success/10',
    },
    {
      label: 'AI 交互次数',
      value: aiStats?.total_interactions ?? 0,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0V5.5a2.25 2.25 0 00-2.25-2.25h-9.5A2.25 2.25 0 002.75 5.5v9" />
        </svg>
      ),
      trend: `满意度 ${(aiStats?.satisfaction_rate ?? 0) * 100}%`,
      trendUp: true,
      color: 'text-purple-600 bg-purple-100',
    },
    {
      label: '培训场次',
      value: trainStats?.total_sessions ?? 0,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
      ),
      trend: `完成率 ${((trainStats?.completion_rate ?? 0) * 100).toFixed(1)}%`,
      trendUp: true,
      color: 'text-cyan-600 bg-cyan-100',
    },
    {
      label: '社区帖子',
      value: commStats?.total_posts ?? 0,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
        </svg>
      ),
      trend: `${commStats?.total_comments ?? 0} 条评论`,
      trendUp: true,
      color: 'text-pink-600 bg-pink-100',
    },
  ];

  const featureBreakdown = aiUsage?.feature_breakdown ?? [];
  const maxFeatureCount = Math.max(...featureBreakdown.map((f) => f.count), 1);
  const topUsers = aiUsage?.top_users ?? [];
  const topPosts = community?.top_posts ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h1 className="text-2xl font-bold text-text">数据看板</h1>
        <Badge className="bg-amber-100 text-amber-700 w-fit">演示模式</Badge>
      </div>

      {/* Period Selector */}
      <div className="flex gap-2">
        {(Object.keys(periodLabels) as Period[]).map((p) => (
          <Button
            key={p}
            variant={period === p ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setPeriod(p)}
          >
            {periodLabels[p]}
          </Button>
        ))}
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {statCards.map((card) => (
          <Card key={card.label} padding="lg">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-muted truncate">{card.label}</p>
                <p className="text-2xl font-bold text-text mt-1">{card.value.toLocaleString()}</p>
              </div>
              <div className={cn('flex items-center justify-center w-10 h-10 rounded-lg', card.color)}>
                {card.icon}
              </div>
            </div>
            <p className={cn('text-xs mt-2', card.trendUp ? 'text-success' : 'text-error')}>
              {card.trendUp ? '↑' : '↓'} {card.trend}
            </p>
          </Card>
        ))}
      </div>

      {/* Second Row: AI Usage + Quick Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: AI Usage */}
        <Card padding="lg">
          <CardTitle>AI 使用情况</CardTitle>
          <CardDescription>各功能模块调用分布</CardDescription>

          {featureBreakdown.length === 0 ? (
            <div className="text-center py-6 text-muted text-sm">暂无数据</div>
          ) : (
            <div className="mt-4 space-y-3">
              {featureBreakdown.map((feature, idx) => (
                <div key={feature.feature} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text font-medium">{feature.label || feature.feature}</span>
                    <span className="text-muted">{feature.count.toLocaleString()} 次 ({feature.percentage}%)</span>
                  </div>
                  <div className="h-6 bg-bg rounded-md overflow-hidden">
                    <div
                      className={cn('h-full rounded-md transition-all duration-500', barColors[idx % barColors.length])}
                      style={{ width: `${(feature.count / maxFeatureCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Top 3 Users */}
          <div className="mt-6 pt-4 border-t border-border">
            <p className="text-sm font-medium text-text mb-3">活跃用户 TOP 3</p>
            {topUsers.length === 0 ? (
              <p className="text-sm text-muted">暂无数据</p>
            ) : (
              <div className="space-y-2">
                {topUsers.slice(0, 3).map((user, idx) => (
                  <div key={user.user_id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold',
                        idx === 0 ? 'bg-amber-100 text-amber-700' : idx === 1 ? 'bg-gray-100 text-gray-600' : 'bg-orange-50 text-orange-600'
                      )}>
                        {idx + 1}
                      </span>
                      <span className="text-sm text-text">{user.name}</span>
                    </div>
                    <span className="text-sm text-muted">{user.usage_count} 次</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Right: Quick Stats */}
        <div className="space-y-6">
          {/* Training Stats */}
          <Card padding="lg">
            <CardTitle>培训数据</CardTitle>
            <CardDescription>培训平均得分与完成情况</CardDescription>

            <div className="mt-4 space-y-4">
              <div>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-muted">平均得分</span>
                  <span className="font-semibold text-text">{training?.avg_score?.toFixed(1) ?? '0.0'} / 100</span>
                </div>
                <div className="h-3 bg-bg rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500"
                    style={{ width: `${(training?.avg_score ?? 0)}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-muted">完成率</span>
                  <span className="font-semibold text-text">{((training?.completion_rate ?? 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="h-3 bg-bg rounded-full overflow-hidden">
                  <div
                    className="h-full bg-success rounded-full transition-all duration-500"
                    style={{ width: `${(training?.completion_rate ?? 0) * 100}%` }}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-bg rounded-lg p-3 text-center">
                  <p className="text-lg font-bold text-text">{training?.total_sessions ?? 0}</p>
                  <p className="text-xs text-muted">总培训场次</p>
                </div>
                <div className="bg-bg rounded-lg p-3 text-center">
                  <p className="text-lg font-bold text-text">{aiUsage?.avg_latency_ms ?? 0}</p>
                  <p className="text-xs text-muted">平均响应(ms)</p>
                </div>
              </div>
            </div>
          </Card>

          {/* Community Top Posts */}
          <Card padding="lg">
            <CardTitle>社区热门帖子</CardTitle>
            <CardDescription>浏览量与点赞数排名</CardDescription>

            {topPosts.length === 0 ? (
              <div className="text-center py-6 text-muted text-sm">暂无数据</div>
            ) : (
              <div className="mt-4 space-y-3">
                {topPosts.slice(0, 3).map((post, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <span className={cn(
                      'flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold shrink-0 mt-0.5',
                      idx === 0 ? 'bg-amber-100 text-amber-700' : idx === 1 ? 'bg-gray-100 text-gray-600' : 'bg-orange-50 text-orange-600'
                    )}>
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-text font-medium truncate">{post.title}</p>
                      <div className="flex gap-3 mt-1 text-xs text-muted">
                        <span>👁 {post.views}</span>
                        <span>👍 {post.likes}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
