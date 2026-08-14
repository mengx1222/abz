import api from './api';

// ---- Types ----

export interface TodayStat {
  label: string;
  value: string;
  sub: string;
  trend: 'up' | 'down' | 'neutral';
}

export interface AiSuggestion {
  id: string;
  title: string;
  description: string;
  tag: string;
  tag_variant: string;
  action_url: string | null;
  created_at: string;
}

export interface QuickAction {
  label: string;
  icon: string;
  path: string;
  color: string;
}

export interface RecentActivity {
  id: string;
  type: string;
  title: string;
  description: string;
  time: string;
  icon: string;
}

export interface DashboardOverview {
  greeting: string;
  user_name: string;
  today_stats: TodayStat[];
  ai_suggestions: AiSuggestion[];
  quick_actions: QuickAction[];
  recent_activities: RecentActivity[];
  unread_notifications: number;
}

// ---- API ----

export async function getDashboard(): Promise<DashboardOverview> {
  const { data } = await api.get('/dashboard');
  return data;
}
