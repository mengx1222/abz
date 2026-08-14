import { Card } from '../../components/ui/Card';

export function ProductQaPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">AI产品专家</h1>
        <p className="text-muted text-sm mt-1">向AI提问任何保险产品相关问题，获取专业解答</p>
      </div>
      <Card padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-5xl mb-4">🤖</span>
          <h2 className="text-lg font-semibold text-text">AI 产品专家</h2>
          <p className="text-sm text-muted mt-2 max-w-md">
            即将上线。您将能够向AI提问任何保险产品问题，
            获取基于知识库的精准解答和对比分析。
          </p>
        </div>
      </Card>
    </div>
  );
}