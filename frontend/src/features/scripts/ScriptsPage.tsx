import { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

interface DemoScript {
  id: string;
  title: string;
  scenario: string;
  description: string;
 tags: string[];
 usageCount: string;
 rating: string;
}

const scenarios = ['全部场景', '首次电销', '跟进回访', '异议处理', '促成签约', '续保提醒'];

const demoScripts: DemoScript[] = [
  {
    id: '1',
    title: '重疾险电销话术',
    scenario: '首次电销',
    description:
      '针对30-45岁中产家庭，从健康风险切入，介绍重疾险核心价值。包含开场白、需求探寻、产品亮点、报价促成四个环节，预计通话时长5-8分钟。',
    tags: ['重疾险', '电销', '中产客群'],
    usageCount: '2,341',
    rating: '4.8',
  },
  {
    id: '2',
    title: '百万医疗险跟进话术',
    scenario: '跟进回访',
    description:
      '适用于首次咨询后3-5天的回访跟进。以最新理赔案例为引入，强化医疗险的高杠杆特性，解答常见疑虑如"有社保还要买吗"。',
    tags: ['百万医疗险', '回访', '高性价比'],
    usageCount: '1,856',
    rating: '4.6',
  },
  {
    id: '3',
    title: '异议处理：太贵了话术',
    scenario: '异议处理',
    description:
      '系统化应对"保费太贵"的异议，从日均成本拆解、风险对冲价值、案例对比三个维度进行说服，配合具体数字增强说服力。',
    tags: ['异议处理', '价格异议', '通用'],
    usageCount: '3,102',
    rating: '4.9',
  },
  {
    id: '4',
    title: '年金险促成话术',
    scenario: '促成签约',
    description:
      '针对有养老规划需求的35-50岁客户，从"退休收入替代率"入手，结合利率下行趋势，引导客户认识年金险的确定性和复利价值。',
    tags: ['年金险', '促成', '养老规划'],
    usageCount: '987',
    rating: '4.5',
  },
  {
    id: '5',
    title: '续保提醒通用话术',
    scenario: '续保提醒',
    description:
      '保单到期前30天标准续保提醒话术，包含保障回顾、新产品升级点说明、续保优惠提示，适用于各险种续保场景。',
    tags: ['续保', '通用', '客户维护'],
    usageCount: '1,543',
    rating: '4.7',
  },
  {
    id: '6',
    title: '少儿险种组合推荐话术',
    scenario: '首次电销',
    description:
      '面向0-12岁孩子家长，推荐"重疾+医疗+意外"组合方案。从教育金储备和健康保障双维度切入，强调"给孩子确定的未来"。',
    tags: ['少儿险', '组合方案', '家长客群'],
    usageCount: '1,290',
    rating: '4.6',
  },
];

export function ScriptsPage() {
  const user = useAuthStore((s) => s.user);
  const [activeScenario, setActiveScenario] = useState('全部场景');

  const filtered =
    activeScenario === '全部场景'
      ? demoScripts
      : demoScripts.filter((s) => s.scenario === activeScenario);

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">AI话术</h1>
            <Badge variant="warning">演示模式</Badge>
          </div>
          <p className="text-muted text-sm mt-1">
            {user?.name || '用户'}，AI生成个性化销售话术，提升沟通效率
          </p>
        </div>
        <Button variant="primary" size="sm" disabled>
          + 生成新话术
        </Button>
      </div>

      {/* Scenario Selector */}
      <div className="flex gap-2 flex-wrap">
        {scenarios.map((s) => (
          <button
            key={s}
            onClick={() => setActiveScenario(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              activeScenario === s
                ? 'bg-accent text-white'
                : 'bg-card border border-border text-muted hover:text-text'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Script Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filtered.map((script) => (
          <Card key={script.id} padding="md" hover>
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle>{script.title}</CardTitle>
                <Badge variant="default">{script.scenario}</Badge>
              </div>
              <CardDescription>{script.description}</CardDescription>
            </CardHeader>
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
              <div className="flex gap-1.5 flex-wrap">
                {script.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 rounded text-xs bg-bg text-muted"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-3 text-xs text-muted shrink-0 ml-2">
                <span>使用 {script.usageCount} 次</span>
                <span>⭐ {script.rating}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <p className="text-xs text-muted text-center">演示模式 — 功能待开发 · 当前展示为示例数据</p>
    </div>
  );
}
