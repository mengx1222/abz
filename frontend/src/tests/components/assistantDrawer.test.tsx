// ---- mock services（文件最顶部注册，确保模块加载时已生效）----
vi.mock('../../services/salesAgentService', () => ({
  AgentHttpError: class AgentHttpError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  streamSalesAgentChat: vi.fn(),
}));

vi.mock('../../services/customerService', () => ({
  listCustomers: vi.fn(),
}));

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { fireEvent } from '@testing-library/react';
import { AssistantDrawer } from '../../components/assistant/AssistantDrawer';
import { useAssistantStore } from '../../stores/assistantStore';
import { streamSalesAgentChat, type AgentEvent } from '../../services/salesAgentService';
import { listCustomers, type Customer } from '../../services/customerService';

const mockedStream = vi.mocked(streamSalesAgentChat);
const mockedList = vi.mocked(listCustomers);

const CUSTOMERS = [
  { id: 'c-1', name: '张三', customer_type: 'prospective', current_stage: 'needs_analysis' },
  { id: 'c-2', name: '李四', customer_type: null, current_stage: null },
] as unknown as Customer[];

async function* eventStream(events: AgentEvent[]): AsyncGenerator<AgentEvent> {
  for (const e of events) yield e;
}

function agentEvent(event: AgentEvent['event'], data: Record<string, unknown>): AgentEvent {
  return { event, data };
}

describe('AssistantDrawer（全局 AI 助手抽屉）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    useAssistantStore.setState({ open: false });
    mockedList.mockResolvedValue({
      items: CUSTOMERS,
      total: 2,
      page: 1,
      pageSize: 20,
      totalPages: 1,
    });
  });

  it('默认关闭时不渲染任何内容', () => {
    const { container } = render(<AssistantDrawer />);
    expect(container).toBeEmptyDOMElement();
  });

  it('打开后显示客户选择器并可选中客户进入对话', async () => {
    useAssistantStore.getState().setOpen(true);
    render(<AssistantDrawer />);

    // 选择器加载客户列表
    await waitFor(() => expect(screen.getByText('张三')).toBeInTheDocument());
    fireEvent.click(screen.getByText('张三'));

    // 进入对话态
    await waitFor(() =>
      expect(screen.getByPlaceholderText('输入问题或销售场景...')).toBeInTheDocument()
    );
    expect(screen.getByText(/正在协助客户：张三/)).toBeInTheDocument();
  });

  it('支持搜索关键词过滤客户列表', async () => {
    useAssistantStore.getState().setOpen(true);
    render(<AssistantDrawer />);
    await waitFor(() => expect(mockedList).toHaveBeenCalled());

    fireEvent.change(screen.getByPlaceholderText('搜索客户姓名...'), {
      target: { value: '李' },
    });
    await waitFor(() =>
      expect(mockedList).toHaveBeenLastCalledWith(expect.objectContaining({ search: '李' }))
    );
  });

  it('发送消息后流式渲染助手回复并保持会话', async () => {
    mockedStream.mockImplementation(() =>
      eventStream([
        agentEvent('agent_start', { session_id: 'sess-9' }),
        agentEvent('message_delta', { content: '建议优先跟进' }),
        agentEvent('message_delta', { content: '高意向客户。' }),
        agentEvent('agent_complete', {
          status: 'completed',
          message: '建议优先跟进高意向客户。',
          rag_status: 'ALLOW',
        }),
      ])
    );

    useAssistantStore.getState().setOpen(true);
    render(<AssistantDrawer />);
    fireEvent.click(await screen.findByText('张三'));

    const input = await screen.findByPlaceholderText('输入问题或销售场景...');
    fireEvent.change(input, { target: { value: '下一步怎么跟进？' } });
    fireEvent.submit(input.closest('form')!);

    expect(await screen.findByText('下一步怎么跟进？')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/建议优先跟进高意向客户。/)).toBeInTheDocument()
    );
    // 回复已落定为完成态，输入框可用
    expect(screen.getByPlaceholderText('输入问题或销售场景...')).not.toBeDisabled();

    // 会话持久化：sessionId 已写入 sessionStorage
    const saved = JSON.parse(sessionStorage.getItem('azb_ai_assistant_v1') || '{}');
    expect(saved.sessionId).toBe('sess-9');
    expect(saved.customerId).toBe('c-1');
  });

  it('Esc 关闭抽屉', async () => {
    useAssistantStore.getState().setOpen(true);
    render(<AssistantDrawer />);
    expect(screen.getByText('AI 助手')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(useAssistantStore.getState().open).toBe(false));
    expect(useAssistantStore.getState().open).toBe(false);
  });
});
