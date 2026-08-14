import { Card } from '../../components/ui/Card';

export function CustomersPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">客户360</h1>
        <p className="text-muted text-sm mt-1">全方位客户视图，AI驱动的客户洞察与需求分析</p>
      </div>
      <Card padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-5xl mb-4">👥</span>
          <h2 className="text-lg font-semibold text-text">客户360</h2>
          <p className="text-sm text-muted mt-2 max-w-md">
            即将上线。您将能够查看客户全景档案、AI分析客户需求、
            获取智能跟进建议。
          </p>
        </div>
      </Card>
    </div>
  );
}