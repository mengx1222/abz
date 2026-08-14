import { Card } from '../../components/ui/Card';

export function CommunityPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">AI社区</h1>
        <p className="text-muted text-sm mt-1">与同事分享经验，AI精选优秀案例和销售心得</p>
      </div>
      <Card padding="lg">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-5xl mb-4">🌐</span>
          <h2 className="text-lg font-semibold text-text">AI社区</h2>
          <p className="text-sm text-muted mt-2 max-w-md">
            即将上线。您将能够浏览同事分享的优秀销售案例，
            AI自动精选和推荐相关内容，与团队协作互助。
          </p>
        </div>
      </Card>
    </div>
  );
}