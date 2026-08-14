import api from './api';

// ---- Types ----

export interface MonthlyStat {
  label: string;
  value: string;
  unit: string;
  change: string;
  up: boolean;
}

export interface WeeklyTrend {
  day: string;
  calls: number;
  deals: number;
}

export interface AbilityScore {
  label: string;
  score: number;
}

export interface LearningCourse {
  id: string;
  title: string;
  progress: number;
  total: string;
  status: string;
  category: string;
  description: string;
}

export interface Lesson {
  id: string;
  title: string;
  completed: boolean;
  duration: string;
}

export interface CourseDetail {
  id: string;
  title: string;
  description: string;
  category: string;
  progress: number;
  total_lessons: number;
  completed_lessons: number;
  status: string;
  lessons: Lesson[];
}

export interface LeaderboardItem {
  rank: number;
  user_name: string;
  org_name: string;
  score: number;
  avatar: string;
}

export interface AchievementItem {
  id: string;
  name: string;
  description: string;
  icon: string;
  unlocked_at: string | null;
  is_unlocked: boolean;
  category: string;
}

export interface GrowthOverview {
  monthly_stats: MonthlyStat[];
  weekly_trend: WeeklyTrend[];
  ability_scores: AbilityScore[];
  learning_courses: LearningCourse[];
  level: number;
  level_name: string;
  exp_current: number;
  exp_next: number;
  total_exp: number;
}

export interface AchievementList {
  unlocked: AchievementItem[];
  locked: AchievementItem[];
}

export interface LeaderboardResponse {
  period: string;
  leaderboard: LeaderboardItem[];
  my_rank: LeaderboardItem | null;
}

// ---- API ----

export async function getGrowthOverview(): Promise<GrowthOverview> {
  const { data } = await api.get('/growth/overview');
  return data;
}

export async function getCourseDetail(courseId: string): Promise<CourseDetail> {
  const { data } = await api.get(`/growth/courses/${courseId}`);
  return data;
}

export async function getLeaderboard(period: string = 'month'): Promise<LeaderboardResponse> {
  const { data } = await api.get('/growth/leaderboard', { params: { period } });
  return data;
}

export async function getAchievements(): Promise<AchievementList> {
  const { data } = await api.get('/growth/achievements');
  return data;
}
