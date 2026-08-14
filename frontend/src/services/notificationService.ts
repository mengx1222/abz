import api from './api';

// ---- Types ----

export interface NotificationItem {
  id: string;
  type: 'system' | 'followup' | 'training' | 'team' | 'achievement';
  title: string;
  content: string;
  time: string;
  created_at: string;
  read: boolean;
  action_url: string | null;
  metadata: Record<string, unknown>;
}

export interface NotificationListResponse {
  notifications: NotificationItem[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
}

export interface NotificationPreference {
  type: string;
  label: string;
  enabled: boolean;
  channel: string[];
}

export interface NotificationPreferencesResponse {
  preferences: NotificationPreference[];
}

// ---- API ----

export async function getNotifications(
  type?: string,
  page: number = 1,
  pageSize: number = 20,
): Promise<NotificationListResponse> {
  const { data } = await api.get('/notifications', {
    params: { type, page, page_size: pageSize },
  });
  return data;
}

export async function markNotificationsRead(
  notificationIds?: string[],
  readAll: boolean = false,
): Promise<{ updated_count: number }> {
  const { data } = await api.post('/notifications/read', {
    notification_ids: notificationIds || [],
    read_all: readAll,
  });
  return data;
}

export async function getNotificationPreferences(): Promise<NotificationPreferencesResponse> {
  const { data } = await api.get('/notifications/preferences');
  return data;
}

export async function updateNotificationPreference(
  type: string,
  enabled?: boolean,
  channel?: string[],
): Promise<NotificationPreference> {
  const { data } = await api.put('/notifications/preferences', { type, enabled, channel });
  return data;
}
