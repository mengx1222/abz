import { Card } from '../../components/ui/Card';

export function TrainingPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">AI陪练</h1>
        <p className="text-muted text-sm mt-1">AI模拟真实销售场景，帮助您提升销售技能</p>
      </div>
      <Card padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-5xl mb-4">🎯</span>
          <h2 className="text-lg font-semibold text-text">AI陪练</h2>
          <p className="text-sm text-muted mt-2 max-w-md">
            即将上线。您将能够与AI进行模拟销售对话练习，
            获得实时反馈和评分，持续提升专业能力。
          </p>
        </div>
      </Card>
    </div>
  );
}