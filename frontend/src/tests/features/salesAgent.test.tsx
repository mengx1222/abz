// ---- mock services（文件最顶部，import 之前注册，确保页面模块加载时已生效）----
vi.mock('../../services/salesAgentService', () => ({
  AgentHttpError: class AgentHttpError extends Error {
    status: number;
    detailMessage?: string;
    constructor(status: number, message: string, detailMessage?: string) {
      super(message);
      this.status = status;
      this.detailMessage = detailMessage;
    }
  },
  streamSalesAgentChat: vi.fn(),
}));

vi.mock('../../services/customerService', () => ({
  getCustomer: vi.fn(),
}));

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { fireEvent, act } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SalesAgentPage } from '../../features/sales-agent/SalesAgentPage';
import {
  AgentHttpError,
  streamSalesAgentChat,
  type AgentEvent,
} from '../../services/salesAgentService';
import { getCustomer } from '../../services/customerService';

const mockedStream = vi.mocked(streamSalesAgentChat);
const mockedGetCustomer = vi.mocked(getCustomer);

const MOCK_CUSTOMER = {
  id: '11111111-1111-1111-1111-111111111111',
  name: '张三',
  age: 35,
  customer_type: 'prospective',
  current_stage: 'needs_analysis',
  intention_level: 4,
  insurance_type: '医疗险',
};

async function* eventStream(events: AgentEvent[]): AsyncGenerator<AgentEvent> {
  for (const e of events) yield e;
}

function agentEvent(
  event: AgentEvent['event'],
  data: Record<string, unknown>
): AgentEvent {
  return { event, data };
}

const COMPLETE_OK = agentEvent('agent_complete', {
  status: 'completed',
  message: '建议先了解客户就医报销需求，再推荐百万医疗险。',
  tool_sequence: ['get_customer_context', 'search_product_knowledge'],
  rag_status: 'ALLOW',
  citations: [],
  compliance: null,
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/sales-agent/11111111-1111-1111-1111-111111111111']}>
      <Routes>
        <Route path="/sales-agent/:customerId?" element={<SalesAgentPage />} />
      </Routes>
    </MemoryRouter>
  );
}

const TEST_TIMEOUT = 20000;

describe('SalesAgentPage（AI 销售副驾）', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockedGetCustomer.mockImplementation(() => Promise.resolve(MOCK_CUSTOMER as never));
  });

  it(
    'initial：加载客户上下文与空对话提示',
    async () => {
      expect(vi.isMockFunction(getCustomer)).toBe(true);
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(mockedGetCustomer).toHaveBeenCalled();
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      expect(screen.getByText('AI 销售副驾已就绪')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('输入销售场景或客户诉求...')).toBeInTheDocument();
    },
    TEST_TIMEOUT
  );

  it(
    '正常 SSE：流式文本 + Citation + Compliance GREEN',
    async () => {
      mockedStream.mockImplementation(() =>
        eventStream([
          agentEvent('agent_start', { session_id: 's1', request_id: 'r1' }),
          agentEvent('tool_planned', { tool: 'get_customer_context', action: '正在查询客户信息' }),
          agentEvent('rag_context', {
            status: 'ALLOW',
            citations: [
              {
                document_id: 'd1',
                document_title: '百万医疗险产品手册',
                section: '保障范围',
                score: 0.91,
              },
            ],
          }),
          agentEvent('message_delta', { content: '建议先了解客户' }),
          agentEvent('message_delta', { content: '就医报销需求。' }),
          agentEvent('compliance', { status: 'GREEN', score: 100, issues: [] }),
          COMPLETE_OK,
        ])
      );

      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);

      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(
        () => {
          expect(screen.getByText(/建议先了解客户就医报销需求/)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
      expect(screen.getByText('正在查询客户信息')).toBeInTheDocument();
      expect(screen.getByText('百万医疗险产品手册')).toBeInTheDocument();
      expect(screen.getByText('保障范围')).toBeInTheDocument();
      expect(screen.getByText('合规通过')).toBeInTheDocument();
      expect(screen.getByText('合规检查通过，内容可正常使用。')).toBeInTheDocument();
    },
    TEST_TIMEOUT
  );

  it(
    'Compliance YELLOW：显示建议人工确认',
    async () => {
      mockedStream.mockImplementation(() =>
        eventStream([
          agentEvent('compliance', {
            status: 'YELLOW',
            score: 80,
            issues: [{ rule: '绝对化表达', severity: 'YELLOW', suggestion: '修改为相对表述' }],
          }),
          agentEvent('agent_complete', {
            status: 'completed',
            message: '这个产品是市场上最好的。',
          }),
        ])
      );
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(() => expect(screen.getByText('建议人工确认')).toBeInTheDocument(), {
        timeout: 3000,
      });
      expect(
        screen.getByText('存在需要人工确认的表述，请修改或复核后再使用。')
      ).toBeInTheDocument();
    },
    TEST_TIMEOUT
  );

  it(
    'Compliance RED：明确禁止直接对客使用',
    async () => {
      mockedStream.mockImplementation(() =>
        eventStream([
          agentEvent('compliance', {
            status: 'RED',
            score: 60,
            issues: [{ rule: '收益承诺', severity: 'RED', suggestion: '以合同条款为准' }],
          }),
          agentEvent('agent_complete', {
            status: 'completed',
            message: '这个产品保证收益稳赚不赔。',
          }),
        ])
      );
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(() => expect(screen.getByText('禁止直接对客使用')).toBeInTheDocument(), {
        timeout: 3000,
      });
      expect(
        screen.getByText('检测到违规表述，该内容不可直接用于客户沟通。')
      ).toBeInTheDocument();
    },
    TEST_TIMEOUT
  );

  it(
    'RAG REFUSE：明确展示无依据安全状态（不渲染成普通答案）',
    async () => {
      mockedStream.mockImplementation(() =>
        eventStream([
          agentEvent('rag_context', { status: 'REFUSE', citations: [] }),
          agentEvent('agent_complete', {
            status: 'completed',
            message: '当前知识库未找到该产品的充分产品依据。',
            rag_status: 'REFUSE',
            citations: [],
          }),
        ])
      );
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(
        () => expect(screen.getByText('⚠️ 当前知识库没有足够的产品依据')).toBeInTheDocument(),
        { timeout: 3000 }
      );
      expect(screen.queryByText('📖 产品知识来源')).not.toBeInTheDocument();
    },
    TEST_TIMEOUT
  );

  it(
    '404：AgentHttpError(404) 显示真实语义 + 重试入口',
    async () => {
      mockedStream.mockRejectedValue(
        new AgentHttpError(404, '客户不存在或无权访问。', '客户不存在或无权访问。')
      );
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(() => expect(screen.getByText('客户不存在或无权访问。')).toBeInTheDocument(), {
        timeout: 3000,
      });
      expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument();
    },
    TEST_TIMEOUT
  );

  it(
    'Provider error：SSE error 事件 → 错误消息 + 重试',
    async () => {
      mockedStream.mockImplementation(() =>
        eventStream([agentEvent('error', { message: '话术生成服务不可用，请稍后重试' })])
      );
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(
        () => expect(screen.getByText('话术生成服务不可用，请稍后重试')).toBeInTheDocument(),
        { timeout: 3000 }
      );
      expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument();
    },
    TEST_TIMEOUT
  );

  it(
    'stream error：网络异常 → 错误消息',
    async () => {
      mockedStream.mockRejectedValue(new Error('网络异常，请检查连接后重试。'));
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(
        () => expect(screen.getByText('网络异常，请检查连接后重试。')).toBeInTheDocument(),
        { timeout: 3000 }
      );
    },
    TEST_TIMEOUT
  );

  it(
    'retry：点击重试会重新发起请求',
    async () => {
      mockedStream.mockRejectedValueOnce(new Error('网络异常，请检查连接后重试。'));
      mockedStream.mockImplementation(() =>
        eventStream([agentEvent('message_delta', { content: '重试成功结果' }), COMPLETE_OK])
      );
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(() => expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument(), {
        timeout: 3000,
      });
      fireEvent.click(screen.getByRole('button', { name: '重试' }));

      await waitFor(() => expect(screen.getByText('重试成功结果')).toBeInTheDocument(), {
        timeout: 3000,
      });
      expect(mockedStream).toHaveBeenCalledTimes(2);
    },
    TEST_TIMEOUT
  );

  it(
    '防重复：streaming 期间发送按钮不可点（中止按钮）',
    async () => {
      let release!: () => void;
      const gate = new Promise<void>((r) => (release = r));
      mockedStream.mockImplementation(async function* () {
        await gate;
        yield agentEvent('message_delta', { content: '结果' });
      });
      renderPage();
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getAllByText('张三').length).toBeGreaterThan(0);
      fireEvent.change(screen.getByPlaceholderText('输入销售场景或客户诉求...'), {
        target: { value: '客户想了解医疗险' },
      });
      fireEvent.click(screen.getByRole('button', { name: '发送' }));

      await waitFor(() => expect(screen.getByRole('button', { name: '中止' })).toBeInTheDocument(), {
        timeout: 3000,
      });
      expect(screen.queryByRole('button', { name: '发送' })).not.toBeInTheDocument();
      release();
    },
    TEST_TIMEOUT
  );

  it(
    '客户 404：页面显示客户不存在或无权访问',
    async () => {
      mockedGetCustomer.mockRejectedValue({ response: { status: 404 } });
      renderPage();
      await waitFor(
        () => expect(screen.getByText('客户不存在或无权访问。')).toBeInTheDocument(),
        { timeout: 3000 }
      );
    },
    TEST_TIMEOUT
  );
});
