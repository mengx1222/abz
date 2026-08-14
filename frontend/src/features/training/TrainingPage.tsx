import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

interface TrainingScenario {
  id: string;
  title: string;
  category: string;
  description: string;
  difficulty: '入门' | '进阶' | '高级';
  duration: string;
  completedCount: number;
  score: number | null;
}

const difficultyVariant: Record<string, 'success' | 'warning' | 'error'> = {
  '入门': 'success',
  '进阶': 'warning',
  '高级': 'error',
};

const demoScenarios: TrainingScenario[] = [
  {
    id: '1',
    title: '异议处理训练：保费太贵',
    category: '异议处理',
    description: '模拟客户提出"保费太贵了，我再考虑考虑"的对话场景。AI将扮演犹豫型客户，考验你的价值传递和成交推动能力。',
    difficulty: '进阶',
    duration: '8分钟',
    completedCount: 156,
    score: null,
  },
  {
    id: '2',
    title: '需求分析训练：家庭保障规划',
    category: '需求分析',
    description: '与AI客户进行深度需求沟通，通过提问挖掘家庭收入、负债、保障缺口等信息，制定合理的保险配置方案。',
    difficulty: '进阶',
    duration: '10分钟',
    completedCount: 203,
    score: 85,
  },
  {
    id: '3',
    title: '电销开场白训练',
    category: '电销技巧',
    description: '练习15秒黄金开场，在有限时间内引起客户兴趣并争取继续对话的机会。AI会模拟不同反应类型的客户。',
    difficulty: '入门',
    duration: '5分钟',
    completedCount: 342,
    score: 92,
  },
  {
    id: '4',
    title: '产品介绍训练：重疾险核心卖点',
    category: '产品知识',
    description: '在3分钟内清晰准确地介绍一款重疾险的核心卖点，包括保障范围、理赔条件、与竞品的差异化优势。',
    difficulty: '入门',
    duration: '6分钟',
    completedCount: 278,
    score: 78,
  },
  {
    id: '5',
    title: '促成签约训练：临门一脚',
    category: '成交技巧',
    description: '模拟客户已产生购买意向但仍在犹豫的场景。练习使用不同促成技巧（假设成交、限时优惠、对比法等）推动签约。',
    difficulty: '高级',
    duration: '8分钟',
    completedCount: 89,
    score: null,
  },
  {
    id: '6',
    title: '客诉处理训练：理赔纠纷',
    category: '异议处理',
    description: '模拟客户对理赔结果不满的投诉场景，考验你的共情能力、问题分析能力和解决方案提供能力。',
    difficulty: '高级',
    duration: '12分钟',
    completedCount: 45,
    score: null,
  },
];

export function TrainingPage() {
  const user = useAuthStore((s) => s.user);

  const completedCount = demoScenarios.filter((s) => s.score !== null).length;
  const avgScore =
    demoScenarios.filter((s) => s.score !== null).reduce((sum, s) => sum + (s.score ?? 0), 0) /
    completedCount;

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-text">AI陪练</h1>
          <Badge variant="warning">演示模式</Badge>
        </div>
        <p className="text-muted text-sm mt-1">
          {user?.name || '用户'}，AI模拟真实销售场景，帮助您提升销售技能
        </p>
      </div>

      {/* Progress Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card padding="md">
          <p className="text-sm text-muted">已完成训练</p>
          <p className="text-2xl font-bold text-text mt-1">
            {completedCount}<span className="text-sm font-normal text-muted">/{demoScenarios.length}</span>
          </p>
        </Card>
        <Card padding="md">
          <p className="text-sm text-muted">平均得分</p>
          <p className="text-2xl font-bold text-accent mt-1">
            {completedCount > 0 ? avgScore.toFixed(0) : '--'}
            <span className="text-sm font-normal text-muted"> 分</span>
          </p>
        </Card>
        <Card padding="md">
          <p className="text-sm text-muted">训练总时长</p>
          <p className="text-2xl font-bold text-text mt-1">
            2.4<span className="text-sm font-normal text-muted"> 小时</span>
          </p>
        </Card>
        <Card padding="md">
          <p className="text-sm text-muted">连续训练</p>
          <p className="text-2xl font-bold text-text mt-1">
            5<span className="text-sm font-normal text-muted"> 天</span>
          </p>
        </Card>
      </div>

      {/* Training Scenarios */}
      <div>
        <h2 className="text-base font-semibold text-text mb-3">训练场景</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {demoScenarios.map((scenario) => (
            <Card key={scenario.id} padding="md" hover>
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-sm leading-snug">{scenario.title}</CardTitle>
                  <Badge variant={difficultyVariant[scenario.difficulty]}>{scenario.difficulty}</Badge>
                </div>
                <CardDescription>{scenario.description}</CardDescription>
              </CardHeader>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
                <div className="flex items-center gap-3 text-xs text-muted">
                  <span>{scenario.duration}</span>
                  <span>{scenario.completedCount} 人已练</span>
                  {scenario.score !== null && (
                    <span className="text-success font-medium">得分 {scenario.score}</span>
                  )}
                </div>
                <Button variant="primary" size="sm" disabled>
                  {scenario.score !== null ? '再次训练' : '开始训练'}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>

      <p className="text-xs text-muted text-center">演示模式 — 功能待开发 · 当前展示为示例数据</p>
    </div>
  );
}
