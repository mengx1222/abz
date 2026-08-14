import { Card } from '../../components/ui/Card';

export function NotificationsPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">消息中心</h1>
        <p className="text-muted text-sm mt-1">查看系统通知、团队消息和AI提醒</p>
      </div>
      <Card padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-5xl mb-4">🔔</span>
          <h2 className="text-lg font-semibold text-text">消息中心</h2>
          <p className="text-sm text-muted mt-2 max-w-md">
            即将上线。您将能够查看所有系统通知、客户跟进提醒、
            团队消息和AI智能推送。
          </p>
        </div>
      </Card>
    </div>
  );
}
