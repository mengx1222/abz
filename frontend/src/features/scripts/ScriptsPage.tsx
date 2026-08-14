import { Card } from '../../components/ui/Card';

export function ScriptsPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">AI话术</h1>
        <p className="text-muted text-sm mt-1">AI生成个性化销售话术，提升沟通效率</p>
      </div>
      <Card padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-5xl mb-4">💬</span>
          <h2 className="text-lg font-semibold text-text">AI话术</h2>
          <p className="text-sm text-muted mt-2 max-w-md">
            即将上线。您将能够根据产品类型、客户特征自动生成个性化销售话术，
            并获得话术优化建议。
          </p>
        </div>
      </Card>
    </div>
  );
}