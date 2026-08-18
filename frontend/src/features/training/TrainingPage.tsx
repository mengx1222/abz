import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { Card, CardTitle, CardDescription, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import {
  getScenarios,
  getSessions,
  type Scenario,
  type TrainingSession,
} from '../../services/trainingService';

// ---- Constants ----

const DIFFICULTY_CONFIG: Record<string, { label: string; variant: 'success' | 'warning' | 'error' }> = {
  easy: { label: '入门', variant: 'success' },
  medium: { label: '进阶', variant: 'warning' },
  hard: { label: '挑战', variant: 'error' },
};

const CATEGORIES = ['全部', '价格异议类', '需求认知类', '慢病客户类', '老年客户类', '家庭客户类', '高净值客户类', '销售技巧类'];

type TabView = 'scenarios' | 'history';

export function TrainingPage() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabView>('scenarios');
  const [activeCategory, setActiveCategory] = useState('全部');
  const [activeDifficulty, setActiveDifficulty] = useState<string | null>(null);

  // Scenarios
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loadingScenarios, setLoadingScenarios] = useState(false);

  // History
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (activeTab === 'scenarios') {
      setLoadingScenarios(true);
      getScenarios({
        difficulty: activeDifficulty,
      }).then((data) => {
        let filtered = data;
        if (activeCategory !== '全部') {
          filtered = data.filter((s) => s.category === activeCategory);
        }
        setScenarios(filtered);
      }).catch(() => setScenarios([])).finally(() => setLoadingScenarios(false));
    }
  }, [activeTab, activeCategory, activeDifficulty]);

  useEffect(() => {
    if (activeTab === 'history') {
      setLoadingHistory(true);
      getSessions().then(setSessions).catch(() => setSessions([])).finally(() => setLoadingHistory(false));
    }
  }, [activeTab]);

  const handleStartTraining = (scenarioId: string) => {
    navigate(`/training/chat/${scenarioId}`);
  };

  const handleViewSession = (sessionId: string, score: number | null) => {
    if (score !== null) {
      navigate(`/training/chat/${sessionId}?mode=review`);
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">AI陪练</h1>
          </div>
          <p className="text-muted text-sm mt-1">
            {user?.name || '用户'}，AI模拟真实客户，练习销售话术并获取专业评分
          </p>
        </div>
        <div className="flex gap-1 bg-card rounded-lg p-0.5 border border-border">
          <button
            onClick={() => setActiveTab('scenarios')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer ${
              activeTab === 'scenarios'
                ? 'bg-accent text-white shadow-sm'
                : 'text-muted hover:text-text'
            }`}
          >
            训练场景
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer ${
              activeTab === 'history'
                ? 'bg-accent text-white shadow-sm'
                : 'text-muted hover:text-text'
            }`}
          >
            历史记录
          </button>
        </div>
      </div>

      {/* Tab: Scenarios */}
      {activeTab === 'scenarios' && (
        <div className="space-y-3">
          {/* Filters */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex gap-1 flex-wrap">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                    activeCategory === cat
                      ? 'bg-accent text-white'
                      : 'bg-card border border-border text-muted hover:text-text'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
            <div className="flex gap-1">
              {Object.entries(DIFFICULTY_CONFIG).map(([key, cfg]) => (
                <button
                  key={key}
                  onClick={() => setActiveDifficulty(activeDifficulty === key ? null : key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer border ${
                    activeDifficulty === key
                      ? `border-current ${cfg.variant === 'success' ? 'bg-emerald-50 text-emerald-600' : cfg.variant === 'warning' ? 'bg-amber-50 text-amber-600' : 'bg-red-50 text-red-600'}`
                      : 'border-border text-muted hover:text-text'
                  }`}
                >
                  {cfg.label}
                </button>
              ))}
            </div>
          </div>

          {/* Scenario Grid */}
          {loadingScenarios ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : scenarios.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4 opacity-20">🎯</div>
              <p className="text-muted text-sm">暂无匹配的训练场景</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {scenarios.map((scenario) => {
                const diffCfg = DIFFICULTY_CONFIG[scenario.difficulty] || DIFFICULTY_CONFIG.medium;
                const persona = scenario.customer_persona;
                return (
                  <Card key={scenario.id} padding="md" hover className="flex flex-col">
                    <CardHeader className="flex-1">
                      <div className="flex items-start justify-between mb-1">
                        <CardTitle className="text-sm">{scenario.title}</CardTitle>
                        <Badge variant={diffCfg.variant}>{diffCfg.label}</Badge>
                      </div>
                      <CardDescription className="text-xs line-clamp-2 mb-2">
                        {scenario.description}
                      </CardDescription>
                      {/* Customer Info */}
                      <div className="flex items-center gap-2 text-xs text-muted mb-2">
                        <span className="px-1.5 py-0.5 rounded bg-rose-50 text-rose-500">
                          {persona?.name || '客户'}
                        </span>
                        <span>{persona?.age}岁</span>
                        {scenario.product_focus && (
                          <Badge variant="default" className="text-[10px]">{scenario.product_focus}</Badge>
                        )}
                      </div>
                      {/* Key Objections */}
                      {persona?.key_objections && persona.key_objections.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {persona.key_objections.map((obj) => (
                            <span key={obj} className="px-1.5 py-0.5 rounded text-[10px] bg-bg text-muted border border-border">
                              {obj}
                            </span>
                          ))}
                        </div>
                      )}
                    </CardHeader>
                    <div className="flex items-center justify-between pt-2 border-t border-border">
                      <span className="text-xs text-muted">{scenario.duration_minutes}分钟</span>
                      <Button variant="primary" size="sm" onClick={() => handleStartTraining(scenario.id)}>
                        开始训练
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}

          <p className="text-xs text-muted text-center mt-2">
            共 {scenarios.length} 个训练场景 · 点击开始进入模拟对话
          </p>
        </div>
      )}

      {/* Tab: History */}
      {activeTab === 'history' && (
        <div className="space-y-3">
          {loadingHistory ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4 opacity-20">📋</div>
              <p className="text-muted text-sm">暂无训练记录</p>
              <button
                onClick={() => setActiveTab('scenarios')}
                className="mt-2 text-sm text-accent hover:underline cursor-pointer"
              >
                去开始第一次训练
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {sessions.map((sess) => (
                <Card
                  key={sess.id}
                  padding="md"
                  hover
                  className={sess.total_score !== null ? 'cursor-pointer' : ''}
                  onClick={() => handleViewSession(sess.id, sess.total_score)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-text">
                          {sess.scenario_title || '训练会话'}
                        </span>
                        <Badge variant={sess.status === 'completed' ? 'success' : 'default'}>
                          {sess.status === 'completed' ? '已完成' : '进行中'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-muted">
                        <span>{sess.message_count} 条消息</span>
                        <span>{sess.started_at}</span>
                      </div>
                    </div>
                    {sess.total_score !== null && (
                      <div className="text-right ml-4">
                        <div className={`text-2xl font-bold ${
                          sess.total_score >= 85 ? 'text-emerald-500' :
                          sess.total_score >= 70 ? 'text-amber-500' : 'text-red-500'
                        }`}>
                          {sess.total_score}
                        </div>
                        <p className="text-[10px] text-muted">综合评分</p>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
