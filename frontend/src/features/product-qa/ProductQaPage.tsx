import { useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';

interface ChatMessage {
  id: number;
  role: 'user' | 'ai';
  content: string;
}

const demoMessages: ChatMessage[] = [
  {
    id: 1,
    role: 'user',
    content: '请帮我对比一下平安福和超级玛丽9号重疾险的区别，哪个更适合30岁男性？',
  },
  {
    id: 2,
    role: 'ai',
    content:
      '好的，我来为您对比这两款热门重疾险产品：\n\n**平安福（2024版）**\n• 保额：最高50万\n• 保障期限：终身\n• 重疾赔付：单次赔付，120种重疾\n• 优势：大品牌、线下服务网络完善、含身故责任\n• 年费参考（30岁男）：约8,500元\n\n**超级玛丽9号**\n• 保额：最高60万\n• 保障期限：可选至70岁/终身\n• 重疾赔付：单次赔付，110种重疾\n• 优势：价格更优、可选癌症二次赔付、互联网产品投保便捷\n• 年费参考（30岁男）：约5,200元（保至终身）\n\n**建议**：如果预算有限且追求性价比，超级玛丽9号更合适；如果更看重品牌服务和线下理赔体验，可考虑平安福。需要我进一步分析某款产品的细节吗？',
  },
  {
    id: 3,
    role: 'user',
    content: '百万医疗险和重疾险有什么区别？需要都买吗？',
  },
  {
    id: 4,
    role: 'ai',
    content:
      '这是两个互补型产品，简单来说：\n\n**百万医疗险** — 解决"看病贵"的问题\n• 报销型：花多少报多少（不超过实际花费）\n• 低保费高保额：30岁约300元/年，保额600万\n• 有免赔额：通常1万元\n• 适合所有人，尤其是预算有限时优先配置\n\n**重疾险** — 解决"收入损失"的问题\n• 给付型：确诊即赔一笔钱，怎么花都行\n• 保额较高：建议至少30-50万\n• 年费较高：30岁约4,000-8,000元/年\n• 弥补生病期间的收入损失和康复费用\n\n**建议**：两者搭配购买最佳。百万医疗险作为基础保障，重疾险提供收入补偿。经济紧张时可先配百万医疗险，再逐步补充重疾险。',
  },
];

export function ProductQaPage() {
  const user = useAuthStore((s) => s.user);
  const [inputValue, setInputValue] = useState('');

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text">AI产品专家</h1>
            <Badge variant="warning">演示模式</Badge>
          </div>
          <p className="text-muted text-sm mt-1">
            {user?.name || '用户'}，向AI提问任何保险产品相关问题，获取专业解答
          </p>
        </div>
      </div>

      {/* Chat Area */}
      <Card padding="none" className="flex flex-col" style={{ height: 'calc(100vh - 240px)', minHeight: '400px' }}>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {demoMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-line ${
                  msg.role === 'user'
                    ? 'bg-accent text-white rounded-br-md'
                    : 'bg-bg text-text rounded-bl-md border border-border'
                }`}
              >
                {msg.role === 'ai' && (
                  <p className="text-xs font-medium text-accent mb-1.5">安诊保 AI 专家</p>
                )}
                {msg.content}
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="border-t border-border p-4">
          <div className="flex gap-2">
            <Input
              placeholder="输入您的问题，例如：30岁适合买什么保险？"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="flex-1"
            />
            <Button variant="primary" disabled>
              发送
            </Button>
          </div>
          <p className="text-xs text-muted mt-2">
            演示模式 — 功能待开发 · 当前展示为预设对话示例
          </p>
        </div>
      </Card>
    </div>
  );
}
