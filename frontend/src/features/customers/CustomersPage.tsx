import { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';

type Stage = '初步接触' | '需求分析' | '方案报价' | '异议处理' | '即将成交' | '已成交';

interface DemoCustomer {
  id: string;
  name: string;
  phone: string;
  insuranceType: string;
  stage: Stage;
  lastContact: string;
  source: string;
}

const stageVariant: Record<Stage, 'default' | 'warning' | 'success' | 'error'> = {
  '初步接触': 'default',
  '需求分析': 'default',
  '方案报价': 'warning',
  '异议处理': 'warning',
  '即将成交': 'success',
  '已成交': 'success',
};

const demoCustomers: DemoCustomer[] = [
  { id: '1', name: '王丽华', phone: '138****6721', insuranceType: '重疾险', stage: '即将成交', lastContact: '2025-01-13', source: '转介绍' },
  { id: '2', name: '李建国', phone: '159****3048', insuranceType: '百万医疗险', stage: '方案报价', lastContact: '2025-01-12', source: '线上咨询' },
  { id: '3', name: '张晓梅', phone: '186****9012', insuranceType: '意外险', stage: '需求分析', lastContact: '2025-01-11', source: '电话邀约' },
  { id: '4', name: '陈志强', phone: '135****4567', insuranceType: '少儿教育金', stage: '初步接触', lastContact: '2025-01-10', source: '线下活动' },
  { id: '5', name: '刘美玲', phone: '188****8234', insuranceType: '重疾险', stage: '异议处理', lastContact: '2025-01-12', source: '老客户转介绍' },
  { id: '6', name: '赵伟', phone: '177****1567', insuranceType: '年金险', stage: '已成交', lastContact: '2025-01-08', source: '电话邀约' },
  { id: '7', name: '孙雪', phone: '139****7890', insuranceType: '百万医疗险', stage: '方案报价', lastContact: '2025-01-13', source: '线上咨询' },
  { id: '8', name: '周明', phone: '156****2345', insuranceType: '定期寿险', stage: '需求分析', lastContact: '2025-01-09', source: '转介绍' },
];

const filterOptions = ['全部', '重疾险', '百万医疗险', '意外险', '少儿教育金', '年金险', '定期寿险'];

export function CustomersPage() {
  const user = useAuthStore((s) => s.user);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('全部');

  const filtered = demoCustomers.filter((c) => {
    const matchSearch = c.name.includes(search) || c.phone.includes(search);
    const matchFilter = activeFilter === '全部' || c.insuranceType === activeFilter;
    return matchSearch && matchFilter;
  });

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">客户360</h1>
            <Badge variant="warning">演示模式</Badge>
          </div>
          <p className="text-muted text-sm mt-1">
            {user?.name || '用户'}，共 {demoCustomers.length} 位客户 · AI驱动客户洞察与需求分析
          </p>
        </div>
        <Button variant="primary" size="sm" disabled>
          + 新增客户
        </Button>
      </div>

      {/* Search & Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <Input
            placeholder="搜索客户姓名或手机号..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            icon={<span>🔍</span>}
            className="sm:w-64"
          />
          <div className="flex gap-2 flex-wrap">
            {filterOptions.map((opt) => (
              <button
                key={opt}
                onClick={() => setActiveFilter(opt)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  activeFilter === opt
                    ? 'bg-accent text-white'
                    : 'bg-bg text-muted hover:text-text'
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Customer Table */}
      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-3 font-medium text-muted">客户姓名</th>
                <th className="text-left px-4 py-3 font-medium text-muted">手机号</th>
                <th className="text-left px-4 py-3 font-medium text-muted">险种</th>
                <th className="text-left px-4 py-3 font-medium text-muted">阶段</th>
                <th className="text-left px-4 py-3 font-medium text-muted">来源</th>
                <th className="text-left px-4 py-3 font-medium text-muted">最近联系</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((customer) => (
                <tr
                  key={customer.id}
                  className="border-b border-border last:border-b-0 hover:bg-bg/50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 font-medium text-text">{customer.name}</td>
                  <td className="px-4 py-3 text-muted">{customer.phone}</td>
                  <td className="px-4 py-3 text-text">{customer.insuranceType}</td>
                  <td className="px-4 py-3">
                    <Badge variant={stageVariant[customer.stage]}>{customer.stage}</Badge>
                  </td>
                  <td className="px-4 py-3 text-muted">{customer.source}</td>
                  <td className="px-4 py-3 text-muted">{customer.lastContact}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="py-12 text-center text-muted text-sm">未找到匹配的客户</div>
        )}
      </Card>

      <p className="text-xs text-muted text-center">演示模式 — 功能待开发 · 当前展示为示例数据</p>
    </div>
  );
}
