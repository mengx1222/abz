import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardTitle, CardDescription } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { useToast } from '../../hooks/useToast';
import {
  getNotifications,
  markNotificationsRead,
  getNotificationPreferences,
  updateNotificationPreference,
  type NotificationItem,
  type NotificationPreference,
} from '../../services/notificationService';

// ---- Type mappings ----

type NotificationType = 'system' | 'followup' | 'training' | 'team' | 'achievement';

const TYPE_META: Record<
  NotificationType,
  { label: string; badgeVariant: 'default' | 'warning' | 'success' | 'error'; barColor: string; description: string }
> = {
  followup: {
    label: '客户跟进',
    badgeVariant: 'warning',
    barColor: 'bg-warning',
    description: '客户跟进提醒和续保到期通知',
  },
  system: {
    label: '系统通知',
    badgeVariant: 'default',
    barColor: 'bg-muted',
    description: '系统公告、维护通知和版本更新',
  },
  training: {
    label: '训练提醒',
    badgeVariant: 'success',
    barColor: 'bg-success',
    description: 'AI训练任务分配和完成提醒',
  },
  team: {
    label: '团队动态',
    badgeVariant: 'default',
    barColor: 'bg-accent',
    description: '团队目标、社区帖子等动态消息',
  },
  achievement: {
    label: '成就通知',
    badgeVariant: 'error',
    barColor: 'bg-error',
    description: '业绩达成、里程碑等成就通知',
  },
};

const TYPE_FILTER_OPTIONS: { key: NotificationType | 'all'; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'followup', label: '客户跟进' },
  { key: 'system', label: '系统通知' },
  { key: 'training', label: '训练提醒' },
  { key: 'team', label: '团队动态' },
  { key: 'achievement', label: '成就通知' },
];

const PAGE_SIZE = 20;

// ---- Helpers ----

function formatTime(timeStr: string): string {
  const now = Date.now();
  const then = new Date(timeStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin}分钟前`;
  if (diffHour < 24) return `${diffHour}小时前`;
  if (diffDay < 30) return `${diffDay}天前`;
  return new Date(timeStr).toLocaleDateString('zh-CN');
}

// ---- Toggle Switch (pure CSS) ----

function ToggleSwitch({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={onToggle}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-accent/30 ${
        enabled ? 'bg-accent' : 'bg-border'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${
          enabled ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

// ---- Main Component ----

export function NotificationsPage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  // --- Tab state ---
  const [activeTab, setActiveTab] = useState<'list' | 'settings'>('list');

  // --- Notification list state ---
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<NotificationType | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [markingAllRead, setMarkingAllRead] = useState(false);

  // --- Settings state ---
  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  const [prefsLoading, setPrefsLoading] = useState(false);
  const [prefsError, setPrefsError] = useState<string | null>(null);
  const [updatingType, setUpdatingType] = useState<string | null>(null);

  // --- Toast helper ---
  const showToast = (message: string, type: 'success' | 'error' | 'warning' | 'default' = 'success') => {
    toast({ title: message, variant: type });
  };

  // --- Fetch notifications ---
  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getNotifications(
        typeFilter === 'all' ? undefined : typeFilter,
        page,
        PAGE_SIZE
      );
      setNotifications(resp.notifications);
      setTotal(resp.total);
      setUnreadCount(resp.unread_count);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '获取通知失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [typeFilter, page]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // --- Fetch preferences ---
  const fetchPreferences = useCallback(async () => {
    setPrefsLoading(true);
    setPrefsError(null);
    try {
      const resp = await getNotificationPreferences();
      setPreferences(resp.preferences);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '获取通知设置失败';
      setPrefsError(message);
    } finally {
      setPrefsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'settings' && preferences.length === 0) {
      fetchPreferences();
    }
  }, [activeTab, preferences.length, fetchPreferences]);

  // --- Mark single notification as read ---
  const handleNotificationClick = async (notification: NotificationItem) => {
    if (!notification.read) {
      try {
        await markNotificationsRead([notification.id]);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notification.id ? { ...n, read: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch {
        // Silently fail - user can still navigate
      }
    }
    if (notification.action_url) {
      navigate(notification.action_url);
    }
  };

  // --- Mark all as read ---
  const handleMarkAllRead = async () => {
    setMarkingAllRead(true);
    try {
      await markNotificationsRead(undefined, true);
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
      showToast('已全部标为已读', 'success');
    } catch {
      showToast('操作失败，请重试', 'error');
    } finally {
      setMarkingAllRead(false);
    }
  };

  // --- Toggle preference ---
  const handleTogglePreference = async (pref: NotificationPreference) => {
    const newEnabled = !pref.enabled;
    setUpdatingType(pref.type);
    try {
      const updated = await updateNotificationPreference(pref.type, newEnabled);
      setPreferences((prev) =>
        prev.map((p) => (p.type === pref.type ? updated : p))
      );
      showToast(
        `${pref.label || pref.type} 已${newEnabled ? '开启' : '关闭'}`,
        'success'
      );
    } catch {
      showToast('保存设置失败，请重试', 'error');
    } finally {
      setUpdatingType(null);
    }
  };

  // --- Pagination ---
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const isFirstPage = page <= 1;
  const isLastPage = page >= totalPages;

  const handlePrevPage = () => {
    if (!isFirstPage) setPage((p) => p - 1);
  };

  const handleNextPage = () => {
    if (!isLastPage) setPage((p) => p + 1);
  };

  // --- Client-side search filter ---
  const displayNotifications = searchQuery.trim()
    ? notifications.filter(
        (n) =>
          n.title.toLowerCase().includes(searchQuery.trim().toLowerCase()) ||
          n.content.toLowerCase().includes(searchQuery.trim().toLowerCase())
      )
    : notifications;

  // --- Render ---

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">消息中心</h1>
            {unreadCount > 0 && (
              <Badge variant="error">{unreadCount} 条未读</Badge>
            )}
          </div>
          <p className="text-muted text-sm mt-1">查看系统通知、团队消息和AI提醒</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        <button
          type="button"
          onClick={() => setActiveTab('list')}
          className={`px-4 py-2.5 text-sm font-medium transition-colors cursor-pointer border-b-2 -mb-px ${
            activeTab === 'list'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted hover:text-text'
          }`}
        >
          通知列表
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('settings')}
          className={`px-4 py-2.5 text-sm font-medium transition-colors cursor-pointer border-b-2 -mb-px ${
            activeTab === 'settings'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted hover:text-text'
          }`}
        >
          通知设置
        </button>
      </div>

      {/* ===== Notification List Tab ===== */}
      {activeTab === 'list' && (
        <div className="space-y-4">
          {/* Toolbar */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px] max-w-sm">
              <Input
                placeholder="搜索通知..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value as NotificationType | 'all');
                setPage(1);
              }}
              className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-text transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent cursor-pointer"
            >
              {TYPE_FILTER_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleMarkAllRead}
              loading={markingAllRead}
              disabled={unreadCount === 0}
            >
              全部已读
            </Button>
          </div>

          {/* Loading State */}
          {loading && (
            <Card padding="lg">
              <LoadingSpinner size="md" text="加载通知中..." />
            </Card>
          )}

          {/* Error State */}
          {!loading && error && (
            <Card padding="lg">
              <div className="text-center py-8">
                <p className="text-error text-sm">{error}</p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-4"
                  onClick={fetchNotifications}
                >
                  重试
                </Button>
              </div>
            </Card>
          )}

          {/* Empty State */}
          {!loading && !error && displayNotifications.length === 0 && (
            <Card padding="lg">
              <div className="text-center py-8 text-muted text-sm">
                {searchQuery.trim()
                  ? '没有找到匹配的通知'
                  : '暂无通知'}
              </div>
            </Card>
          )}

          {/* Notification List */}
          {!loading && !error && displayNotifications.length > 0 && (
            <>
              <div className="space-y-2">
                {displayNotifications.map((notification) => {
                  const meta = TYPE_META[notification.type] || TYPE_META.system;
                  return (
                    <Card
                      key={notification.id}
                      padding="md"
                      hover
                      className={`relative ${!notification.read ? 'bg-accent/5' : ''}`}
                      onClick={() => handleNotificationClick(notification)}
                    >
                      <div className="flex items-start gap-3">
                        {/* Left: type color bar + read/unread dot */}
                        <div className="flex items-center gap-2.5 pt-1">
                          <div
                            className={`w-1 h-10 rounded-full shrink-0 ${meta.barColor}`}
                          />
                          <div
                            className={`w-2 h-2 rounded-full shrink-0 ${
                              notification.read ? 'bg-transparent' : 'bg-accent'
                            }`}
                          />
                        </div>

                        {/* Right: title + content + time */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <CardTitle
                              className={`text-sm ${
                                notification.read ? 'font-medium' : 'font-semibold'
                              }`}
                            >
                              {notification.title}
                            </CardTitle>
                            <Badge variant={meta.badgeVariant}>{meta.label}</Badge>
                          </div>
                          <CardDescription className="mt-1 text-xs leading-relaxed">
                            {notification.content}
                          </CardDescription>
                          <p className="text-xs text-muted/60 mt-1.5">
                            {formatTime(notification.time || notification.created_at)}
                          </p>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted">
                  第 {page} 页 / 共 {totalPages} 页
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={isFirstPage}
                    onClick={handlePrevPage}
                  >
                    上一页
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={isLastPage}
                    onClick={handleNextPage}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ===== Settings Tab ===== */}
      {activeTab === 'settings' && (
        <div className="space-y-3">
          {prefsLoading && (
            <Card padding="lg">
              <LoadingSpinner size="md" text="加载设置中..." />
            </Card>
          )}

          {prefsError && (
            <Card padding="lg">
              <div className="text-center py-8">
                <p className="text-error text-sm">{prefsError}</p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-4"
                  onClick={fetchPreferences}
                >
                  重试
                </Button>
              </div>
            </Card>
          )}

          {!prefsLoading && !prefsError && preferences.length > 0 && (
            preferences.map((pref) => {
              const meta = TYPE_META[pref.type as NotificationType];
              const label = pref.label || meta?.label || pref.type;
              const description = meta?.description || '';
              const isUpdating = updatingType === pref.type;
              return (
                <Card key={pref.type} padding="md">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-sm">{label}</CardTitle>
                        {meta && <Badge variant={meta.badgeVariant}>{meta.label}</Badge>}
                      </div>
                      <CardDescription className="mt-0.5 text-xs">
                        {description}
                      </CardDescription>
                    </div>
                    <div className={isUpdating ? 'opacity-50' : ''}>
                      <ToggleSwitch
                        enabled={pref.enabled}
                        onToggle={() => handleTogglePreference(pref)}
                      />
                    </div>
                  </div>
                </Card>
              );
            })
          )}

          {!prefsLoading && !prefsError && preferences.length === 0 && (
            <Card padding="lg">
              <div className="text-center py-8 text-muted text-sm">暂无通知设置项</div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
