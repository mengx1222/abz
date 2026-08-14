import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { getDashboard, type DashboardOverview } from '../../services/dashboardService';

type BadgeVariant = 'default' | 'warning' | 'error' | 'success';

function getFallbackGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 6) return '凌晨好';
  if (hour < 9) return '早上好';
  if (hour < 12) return '上午好';
  if (hour < 14) return '中午好';
  if (hour < 17) return '下午好';
  if (hour < 19) return '傍晚好';
  return '晚上好';
}

const validBadgeVariants = new Set<string>(['default', 'warning', 'error', 'success']);

function toBadgeVariant(raw: string): BadgeVariant {
  return validBadgeVariants.has(raw) ? (raw as BadgeVariant) : 'default';
}

function LoadingSkeleton() {
  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-pulse">
      <div className="space-y-2">
        <div className="h-7 w-48 rounded bg-bg" />
        <div className="h-4 w-64 rounded bg-bg" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card border border-border rounded-xl p-4 h-24" />
        ))}
      </div>
      <div className="space-y-3">
        <div className="h-5 w-24 rounded bg-bg" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-bg" />
          ))}
        </div>
      </div>
      <div className="space-y-3">
        <div className="h-5 w-28 rounded bg-bg" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-bg" />
          ))}
        </div>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="max-w-5xl mx-auto flex flex-col items-center justify-center py-20 text-center">
      <p className="text-muted text-sm mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 text-sm font-medium rounded-lg bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
      >
        重试
      </button>
    </div>
  );
}

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchDashboard() {
      setLoading(true);
      setError(null);
      try {
        const overview = await getDashboard();
        if (!cancelled) {
          setData(overview);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const msg =
            err instanceof Error ? err.message : '加载仪表盘数据失败，请稍后重试';
          setError(msg);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchDashboard();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <LoadingSkeleton />;
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  if (!data) return null;

  const greeting = data.greeting || getFallbackGreeting();
  const displayName = data.user_name || user?.name || '用户';
  const todayStr = new Date().toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-text">
          {greeting}，{displayName}
        </h1>
        <p className="text-muted text-sm mt-1">
          {user?.role_name || '代理人'} · 今天是{todayStr}
        </p>
      </div>

      {/* Quick Actions */}
      {data.quick_actions.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {data.quick_actions.map((action) => (
            <button
              key={action.path}
              onClick={() => navigate(action.path)}
              className="bg-card border border-border rounded-xl p-4 hover:shadow-md transition-all duration-200 cursor-pointer text-left group"
            >
              <span className={`text-2xl block mb-2 ${action.color}`}>{action.icon}</span>
              <p className="text-sm font-medium text-text group-hover:text-accent transition-colors">
                {action.label}
              </p>
            </button>
          ))}
        </div>
      )}

      {/* Today Stats */}
      {data.today_stats.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-text mb-3">今日工作</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {data.today_stats.map((stat) => (
              <Card key={stat.label} padding="md">
                <p className="text-sm text-muted">{stat.label}</p>
                <p className="text-2xl font-bold text-text mt-1">{stat.value}</p>
                <p className="text-xs text-muted mt-1">{stat.sub}</p>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* AI Suggestions */}
      {data.ai_suggestions.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-text mb-3">AI 今日建议</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.ai_suggestions.map((s) => (
              <Card key={s.id} padding="md" hover>
                <div className="flex items-start justify-between mb-2">
                  <CardTitle className="text-sm leading-snug">{s.title}</CardTitle>
                  <Badge variant={toBadgeVariant(s.tag_variant)}>{s.tag}</Badge>
                </div>
                <CardDescription className="text-xs leading-relaxed">
                  {s.description}
                </CardDescription>
              </Card>
            ))}
            </div>
          </div>
      )}
    </div>
  );
}
