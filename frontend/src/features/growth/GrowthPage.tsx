import { Card } from '../../components/ui/Card';

export function GrowthPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">我的成长</h1>
        <p className="text-muted text-sm mt-1">追踪个人成长轨迹，AI定制学习路径</p>
      </div>
      <Card padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-5xl mb-4">📊</span>
          <h2 className="text-lg font-semibold text-text">我的成长</h2>
          <p className="text-sm text-muted mt-2 max-w-md">
            即将上线。您将能够查看个人能力雷达图、学习进度、
            AI定制的学习计划和能力提升建议。
          </p>
        </div>
      </Card>
    </div>
  );
}
