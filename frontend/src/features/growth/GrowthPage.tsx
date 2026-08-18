import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  getGrowthOverview,
  getCourseDetail,
  getLeaderboard,
  getAchievements,
} from '../../services/growthService';
import type {
  GrowthOverview,
  CourseDetail,
  LeaderboardResponse,
  AchievementList,
} from '../../services/growthService';

type TabKey = 'learning' | 'leaderboard' | 'achievements';

const tabs: { key: TabKey; label: string }[] = [
  { key: 'learning', label: '学习中心' },
  { key: 'leaderboard', label: '排行榜' },
  { key: 'achievements', label: '成就中心' },
];

const statusVariant = (status: string): 'warning' | 'success' | 'default' => {
  if (status === '已完成') return 'success';
  if (status === '进行中') return 'warning';
  return 'default';
};

const rankStyle = (rank: number) => {
  if (rank === 1) return 'bg-yellow-50 border-yellow-300';
  if (rank === 2) return 'bg-gray-50 border-gray-300';
  if (rank === 3) return 'bg-orange-50 border-orange-300';
  return '';
};

const rankBadge = (rank: number) => {
  if (rank === 1) return 'bg-yellow-400 text-white';
  if (rank === 2) return 'bg-gray-400 text-white';
  if (rank === 3) return 'bg-orange-400 text-white';
  return 'bg-bg text-muted';
};

export function GrowthPage() {
  const user = useAuthStore((s) => s.user);
  const [activeTab, setActiveTab] = useState<TabKey>('learning');

  // --- Learning tab state ---
  const [overview, setOverview] = useState<GrowthOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // --- Course detail modal state ---
  const [courseDetail, setCourseDetail] = useState<CourseDetail | null>(null);
  const [courseDetailLoading, setCourseDetailLoading] = useState(false);
  // P1-3：后端课程表未落库，生产模式 course_detail 返回 None → 显示空状态
  const [courseDetailEmpty, setCourseDetailEmpty] = useState(false);

  // --- Leaderboard state ---
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null);
  const [lbPeriod, setLbPeriod] = useState('week');
  const [lbLoading, setLbLoading] = useState(true);
  const [lbError, setLbError] = useState<string | null>(null);

  // --- Achievements state ---
  const [achievements, setAchievements] = useState<AchievementList | null>(null);
  const [achLoading, setAchLoading] = useState(false);
  const [achError, setAchError] = useState<string | null>(null);

  // --- Load overview ---
  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true);
    setOverviewError(null);
    try {
      const data = await getGrowthOverview();
      setOverview(data);
    } catch (e: any) {
      setOverviewError(e?.message || '加载失败');
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  // --- Load leaderboard ---
  const fetchLeaderboard = useCallback(async (period: string) => {
    setLbLoading(true);
    setLbError(null);
    try {
      const data = await getLeaderboard(period);
      setLeaderboard(data);
    } catch (e: any) {
      setLbError(e?.message || '加载失败');
    } finally {
      setLbLoading(false);
    }
  }, []);

  // --- Load achievements ---
  const fetchAchievements = useCallback(async () => {
    setAchLoading(true);
    setAchError(null);
    try {
      const data = await getAchievements();
      setAchievements(data);
    } catch (e: any) {
      setAchError(e?.message || '加载失败');
    } finally {
      setAchLoading(false);
    }
  }, []);

  // Initial load for learning tab
  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  // Lazy load leaderboard when tab switches
  useEffect(() => {
    if (activeTab === 'leaderboard' && !leaderboard && !lbLoading) {
      fetchLeaderboard(lbPeriod);
    }
  }, [activeTab, leaderboard, lbLoading, lbPeriod, fetchLeaderboard]);

  // Lazy load achievements when tab switches
  useEffect(() => {
    if (activeTab === 'achievements' && !achievements && !achLoading) {
      fetchAchievements();
    }
  }, [activeTab, achievements, achLoading, fetchAchievements]);

  // --- Course detail modal ---
  const openCourseDetail = async (courseId: string) => {
    setCourseDetailLoading(true);
    setCourseDetailEmpty(false);
    try {
      const detail = await getCourseDetail(courseId);
      if (detail) {
        setCourseDetail(detail);
      } else {
        // P1-3：课程详情未开放（生产返回 None）→ 友好空状态，不崩溃
        setCourseDetail(null);
        setCourseDetailEmpty(true);
      }
    } catch {
      setCourseDetail(null);
      setCourseDetailEmpty(true);
    } finally {
      setCourseDetailLoading(false);
    }
  };

  const closeCourseDetail = () => {
    setCourseDetail(null);
    setCourseDetailEmpty(false);
  };

  // --- Helpers ---
  const expPercent = overview
    ? Math.round((overview.exp_current / overview.exp_next) * 100)
    : 0;

  const maxCalls = overview
    ? Math.max(...overview.weekly_trend.map((d) => d.calls), 1)
    : 1;

  // --- Renderers ---
  const renderLoading = (msg?: string) => (
    <div className="flex items-center justify-center py-20 text-muted text-sm">
      <svg className="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {msg || '加载中...'}
    </div>
  );

  const renderError = (msg: string, onRetry?: () => void) => (
    <div className="flex flex-col items-center justify-center py-20 text-muted text-sm gap-2">
      <p className="text-error">{msg}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>重试</Button>
      )}
    </div>
  );

  // ==================== LEARNING TAB ====================
  const renderLearningTab = () => {
    if (overviewLoading) return renderLoading('正在加载成长数据...');
    if (overviewError) return renderError(overviewError, fetchOverview);
    if (!overview) return null;

    return (
      <div className="space-y-4">
        {/* Level & Exp Bar */}
        <Card padding="md">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-text">{overview.level_name}</span>
              <span className="text-xs text-muted">Lv.{overview.level}</span>
            </div>
            <span className="text-xs text-muted">总经验 {overview.total_exp}</span>
          </div>
          <div className="h-2 rounded-full bg-primary/20 overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${expPercent}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted mt-1">
            <span>{overview.exp_current} EXP</span>
            <span>{overview.exp_next} EXP</span>
          </div>
        </Card>

        {/* Monthly Stats */}
        <div>
          <h2 className="text-base font-semibold text-text mb-3">本月业绩</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {overview.monthly_stats.map((stat) => (
              <Card key={stat.label} padding="md">
                <p className="text-sm text-muted">{stat.label}</p>
                <div className="flex items-baseline gap-1 mt-1">
                  <p className="text-2xl font-bold text-text">{stat.value}</p>
                  <p className="text-sm text-muted">{stat.unit}</p>
                </div>
                <p className={`text-xs mt-1 ${stat.up ? 'text-green-500' : 'text-red-500'}`}>
                  {stat.up ? '\u2191' : '\u2193'} {stat.change} 较上月
                </p>
              </Card>
            ))}
          </div>
        </div>

        {/* Weekly Trend Chart */}
        <Card padding="md">
          <CardHeader>
            <CardTitle>本周通话趋势</CardTitle>
            <CardDescription>每日通话量与成交数对比</CardDescription>
          </CardHeader>
          <div className="flex items-end gap-2 h-32 mt-2">
            {overview.weekly_trend.map((day) => (
              <div key={day.day} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex gap-0.5 items-end justify-center" style={{ height: '100px' }}>
                  <div
                    className="w-3/5 bg-blue-400/80 rounded-t-sm"
                    style={{ height: `${(day.calls / maxCalls) * 100}%` }}
                    title={`通话 ${day.calls}`}
                  />
                  <div
                    className="w-2/5 bg-green-400/80 rounded-t-sm"
                    style={{ height: `${(day.deals / maxCalls) * 100}%` }}
                    title={`成交 ${day.deals}`}
                  />
                </div>
                <span className="text-xs text-muted">{day.day}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-4 mt-3 text-xs text-muted">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-blue-400/80 inline-block" /> 通话量</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-green-400/80 inline-block" /> 成交数</span>
          </div>
        </Card>

        {/* Two-column: Ability Scores + Learning Courses */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Ability Scores */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>能力评估</CardTitle>
              <CardDescription>AI综合评估您的专业能力</CardDescription>
            </CardHeader>
            <div className="space-y-3 mt-2">
              {overview.ability_scores.map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-text">{item.label}</span>
                    <span className="text-muted">{item.score}/100</span>
                  </div>
                  <div className="h-2 rounded-full bg-primary/20 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        item.score >= 80 ? 'bg-green-500' : item.score >= 65 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${item.score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Learning Courses */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>学习进度</CardTitle>
              <CardDescription>AI推荐的学习课程</CardDescription>
            </CardHeader>
            {overview.learning_courses.length === 0 ? (
              /* P1-3：课程表未落库（生产 learning_courses 为空）→ 友好空状态 */
              <p className="text-sm text-muted py-6 text-center">暂无学习课程，敬请期待</p>
            ) : (
            <div className="space-y-3 mt-2">
              {overview.learning_courses.map((course) => (
                <div
                  key={course.id}
                  className="cursor-pointer hover:bg-bg/50 rounded-lg p-2 -m-2 transition-colors"
                  onClick={() => openCourseDetail(course.id)}
                >
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-text truncate mr-2">{course.title}</span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge variant="default">{course.category}</Badge>
                      <Badge variant={statusVariant(course.status)}>{course.status}</Badge>
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-primary/20 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${course.progress === 100 ? 'bg-green-500' : 'bg-primary'}`}
                      style={{ width: `${course.progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted mt-1">{course.total}</p>
                </div>
              ))}
            </div>
            )}
          </Card>
        </div>
      </div>
    );
  };

  // ==================== LEADERBOARD TAB ====================
  const renderLeaderboardTab = () => {
    if (lbLoading) return renderLoading('正在加载排行榜...');
    if (lbError) return renderError(lbError, () => fetchLeaderboard(lbPeriod));
    if (!leaderboard) return null;

    return (
      <div className="space-y-4">
        {/* Period Selector */}
        <div className="flex gap-2">
          {[
            { key: 'week', label: '本周' },
            { key: 'month', label: '本月' },
            { key: 'quarter', label: '本季度' },
          ].map((p) => (
            <Button
              key={p.key}
              variant={lbPeriod === p.key ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => {
                setLbPeriod(p.key);
                setLeaderboard(null);
                fetchLeaderboard(p.key);
              }}
            >
              {p.label}
            </Button>
          ))}
        </div>

        {/* Leaderboard List */}
        <Card padding="md">
          <div className="divide-y divide-border">
            {leaderboard.leaderboard.map((item) => {
              const isMe = leaderboard.my_rank && item.rank === leaderboard.my_rank.rank;
              return (
                <div
                  key={item.rank}
                  className={`flex items-center gap-3 py-3 px-2 rounded-lg transition-colors ${
                    rankStyle(item.rank)
                  } ${isMe ? 'ring-2 ring-blue-400 bg-blue-50/50' : ''}`}
                >
                  {/* Rank */}
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${rankBadge(item.rank)}`}
                  >
                    {item.rank}
                  </div>

                  {/* Avatar (first letter) */}
                  <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold text-primary shrink-0">
                    {item.user_name.charAt(0)}
                  </div>

                  {/* Name & Org */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text truncate">
                      {item.user_name}
                      {isMe && <span className="text-xs text-muted ml-1">(我)</span>}
                    </p>
                    <p className="text-xs text-muted truncate">{item.org_name}</p>
                  </div>

                  {/* Score */}
                  <span className="text-sm font-bold text-text shrink-0">{item.score}</span>
                </div>
              );
            })}
          </div>

          {/* My Rank - if not in list */}
          {leaderboard.my_rank && !leaderboard.leaderboard.some((i) => i.rank === leaderboard.my_rank!.rank) && (
            <div className="mt-4 p-3 rounded-lg ring-2 ring-blue-400 bg-blue-50/50 flex items-center gap-3">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${rankBadge(leaderboard.my_rank.rank)}`}>
                {leaderboard.my_rank.rank}
              </div>
              <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold text-primary shrink-0">
                {leaderboard.my_rank.user_name.charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text truncate">
                  {leaderboard.my_rank.user_name} <span className="text-xs text-muted">(我)</span>
                </p>
                <p className="text-xs text-muted truncate">{leaderboard.my_rank.org_name}</p>
              </div>
              <span className="text-sm font-bold text-text shrink-0">{leaderboard.my_rank.score}</span>
            </div>
          )}
        </Card>
      </div>
    );
  };

  // ==================== ACHIEVEMENTS TAB ====================
  const renderAchievementsTab = () => {
    if (achLoading) return renderLoading('正在加载成就...');
    if (achError) return renderError(achError, fetchAchievements);
    if (!achievements) return null;

    const renderAchievementCard = (item: (typeof achievements.unlocked)[0], locked: boolean) => (
      <Card
        key={item.id}
        padding="md"
        className={locked ? 'opacity-60' : ''}
      >
        <div className="text-3xl mb-2">{item.icon}</div>
        <h3 className="text-sm font-semibold text-text">{item.name}</h3>
        <p className="text-xs text-muted mt-1 line-clamp-2">{item.description}</p>
        {item.unlocked_at && (
          <p className="text-xs text-muted mt-2">{item.unlocked_at}</p>
        )}
      </Card>
    );

    return (
      <div className="space-y-6">
        {/* Unlocked */}
        <div>
          <h2 className="text-base font-semibold text-text mb-3">
            已解锁 ({achievements.unlocked.length})
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {achievements.unlocked.map((item) => renderAchievementCard(item, false))}
          </div>
        </div>

        {/* Locked */}
        <div>
          <h2 className="text-base font-semibold text-text mb-3">
            未解锁 ({achievements.locked.length})
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {achievements.locked.map((item) => renderAchievementCard(item, true))}
          </div>
        </div>
      </div>
    );
  };

  // ==================== COURSE DETAIL MODAL ====================
  const renderCourseDetailModal = () => {
    if (!courseDetail && !courseDetailLoading && !courseDetailEmpty) return null;

    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        onClick={closeCourseDetail}
      >
        <div
          className="bg-white rounded-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col shadow-xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Modal Header */}
          <div className="flex items-start justify-between p-4 border-b border-border">
            <div className="flex-1 min-w-0 mr-3">
              <h2 className="text-lg font-bold text-text truncate">{courseDetail?.title}</h2>
              {courseDetail && (
                <>
                  <p className="text-sm text-muted mt-1">{courseDetail.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant="default">{courseDetail.category}</Badge>
                    <Badge variant={statusVariant(courseDetail.status)}>{courseDetail.status}</Badge>
                  </div>
                  <div className="mt-2">
                    <div className="h-2 rounded-full bg-primary/20 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${courseDetail.progress === 100 ? 'bg-green-500' : 'bg-primary'}`}
                        style={{ width: `${courseDetail.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted mt-1">
                      {courseDetail.completed_lessons}/{courseDetail.total_lessons} 课时已完成 ({courseDetail.progress}%)
                    </p>
                  </div>
                </>
              )}
            </div>
            <button
              onClick={closeCourseDetail}
              className="text-muted hover:text-text transition-colors p-1"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Lessons List */}
          <div className="flex-1 overflow-y-auto p-4">
            {courseDetailLoading ? (
              <div className="flex items-center justify-center py-10 text-muted text-sm">加载中...</div>
            ) : courseDetail ? (
              <div className="space-y-2">
                {courseDetail.lessons.map((lesson, idx) => (
                  <div
                    key={lesson.id}
                    className={`flex items-center gap-3 py-2 px-3 rounded-lg ${
                      lesson.completed ? 'bg-green-50' : 'bg-bg'
                    }`}
                  >
                    {/* Checkbox */}
                    <div
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ${
                        lesson.completed
                          ? 'bg-green-500 border-green-500'
                          : 'border-gray-300'
                      }`}
                    >
                      {lesson.completed && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>

                    {/* Lesson Info */}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${lesson.completed ? 'text-muted line-through' : 'text-text'}`}>{lesson.title}</p>
                    </div>

                    {/* Duration */}
                    <span className="text-xs text-muted shrink-0">{lesson.duration}</span>
                  </div>
                ))}
              </div>
            ) : (
              /* P1-3：详情未开放（生产返回 None）→ 友好空状态，不崩溃 */
              <p className="text-sm text-muted py-10 text-center">
                该课程详情暂未开放，敬请期待
              </p>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ==================== MAIN RENDER ====================
  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">我的成长</h1>
        <p className="text-muted text-sm mt-1">
          {user?.name || '用户'}，追踪个人成长轨迹，AI定制学习路径
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === tab.key
                ? 'border-primary text-primary'
                : 'border-transparent text-muted hover:text-text'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'learning' && renderLearningTab()}
      {activeTab === 'leaderboard' && renderLeaderboardTab()}
      {activeTab === 'achievements' && renderAchievementsTab()}

      {/* Course Detail Modal */}
      {renderCourseDetailModal()}
    </div>
  );
}
