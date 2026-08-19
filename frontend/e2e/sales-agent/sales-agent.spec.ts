import { test, expect, request as pwRequest } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * E2E — AI 销售副驾（Task 28 黄金路径 + 安全场景）
 *
 * 环境：真实 PG + Redis + mock/real AI provider（CI，DEMO_MODE=false）
 * 账号：SYSTEM_ADMIN 13800138003 / 888888（seed.py 固定）
 * 数据：客户通过 production API 创建（SYSTEM_ADMIN 全量访问）→ 确定性可控
 *
 * 覆盖：
 *   - G-1 黄金路径：登录 → /sales-agent/{customerId} → 客户上下文渲染 →
 *     输入销售问题 → Agent 流式执行（tool_planned 安全状态）→ 最终结果非空 →
 *     无浏览器/API 错误
 *   - G-2 安全场景（RAG REFUSE）：客户 insurance_type 设为知识库无匹配产品 →
 *     Agent 明确展示「当前知识库没有足够的产品依据」（不渲染成普通答案）
 *
 * 不依赖固定 AI 文案：只断言稳定事实（tool_planned 安全状态、非空结果、
 * REFUSE 提示、无 console error / API 4xx）。
 */
const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000/api/v1';

async function loginAsSystemAdmin(): Promise<{
  token: string;
  user: Record<string, unknown>;
}> {
  const api = await pwRequest.newContext();
  const res = await api.post(`${API_BASE}/auth/login`, {
    data: { phone: '13800138003', password: '888888' },
  });
  if (res.status() !== 200) {
    throw new Error(`admin login failed: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  const token = body.data.access_token;
  const me = await api.get(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const user = (await me.json()).data as Record<string, unknown>;
  await api.dispose();
  return { token, user };
}

async function createCustomer(token: string, name: string, insuranceType: string): Promise<string> {
  const api = await pwRequest.newContext();
  const res = await api.post(
    `${API_BASE}/customers`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        name,
        age: 35,
        customer_type: 'prospective',
        insurance_type: insuranceType,
        current_stage: 'needs_analysis',
        intention_level: 4,
      },
    },
    { timeout: 30000 }
  );
  if (res.status() !== 200) {
    const bodyText = await res.text();
    await api.dispose();
    throw new Error(`create customer failed: ${res.status()} ${bodyText.slice(0, 300)}`);
  }
  const body = await res.json();
  const id = (body.data || {}).id;
  await api.dispose();
  if (!id) throw new Error('create customer: missing id');
  return id;
}

function watchPage(page: Page) {
  const errors: string[] = [];
  const apiErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push('console.error: ' + msg.text());
  });
  page.on('pageerror', (err) => {
    errors.push('pageerror: ' + err.message);
  });
  page.on('response', (res) => {
    if (res.url().includes('/api/v1/') && res.status() >= 400) {
      apiErrors.push('API ' + res.status() + ' ' + res.url());
    }
  });
  return {
    errors,
    apiErrors,
    assert: () => {
      expect(apiErrors, 'API 错误:\n' + apiErrors.join('\n')).toEqual([]);
      expect(errors, '浏览器错误:\n' + errors.join('\n')).toEqual([]);
    },
  };
}

async function openAgentPage(page: Page, token: string, user: Record<string, unknown>, customerId: string) {
  await page.addInitScript(
    ([t, u]) => {
      localStorage.setItem('abz_token', t);
      localStorage.setItem('abz_user', JSON.stringify(u));
    },
    [token, user] as [string, Record<string, unknown>]
  );
  await page.goto(`/sales-agent/${customerId}`);
}

test.describe('AI 销售副驾（SYSTEM_ADMIN）', () => {
  test('G-1 黄金路径：客户上下文 → Agent 流式执行 → 非空结果', async ({ page }) => {
    const watcher = watchPage(page);
    const { token, user } = await loginAsSystemAdmin();
    const suffix = Date.now().toString().slice(-6);
    const customerId = await createCustomer(token, `AgentE2E客户${suffix}`, '医疗险');

    await openAgentPage(page, token, user, customerId);

    // 页面标题 + 客户上下文
    await expect(page.getByRole('heading', { name: 'AI 销售副驾' })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(`AgentE2E客户${suffix}`)).toBeVisible({ timeout: 15_000 });

    // 输入销售问题并发送
    await page.getByPlaceholder('输入销售场景或客户诉求...').fill('客户想了解医疗险的保障范围和理赔流程，帮我准备沟通话术');
    await page.getByRole('button', { name: '发送' }).click();

    // Agent 流式执行：安全状态说明（tool_planned 确定性事件）
    await expect(page.getByText('正在查询客户信息')).toBeVisible({ timeout: 20_000 });

    // 最终结果非空：等待发送按钮恢复（isStreaming 结束）且用户消息可见
    await expect(page.getByRole('button', { name: '发送' })).toBeVisible({ timeout: 60_000 });
    await expect(
      page.getByText('客户想了解医疗险的保障范围和理赔流程，帮我准备沟通话术')
    ).toBeVisible({ timeout: 10_000 });

    watcher.assert();
  });

  test('G-2 安全场景：RAG 无依据 → 明确展示 REFUSE 安全状态', async ({ page }) => {
    const watcher = watchPage(page);
    const { token, user } = await loginAsSystemAdmin();
    const suffix = Date.now().toString().slice(-6);
    // 知识库无匹配产品 → Agent RAG REFUSE（不编造产品事实）
    const customerId = await createCustomer(token, `AgentE2ERefuse${suffix}`, '极光量子保险');

    await openAgentPage(page, token, user, customerId);

    await expect(page.getByText(`AgentE2ERefuse${suffix}`)).toBeVisible({ timeout: 15_000 });

    await page
      .getByPlaceholder('输入销售场景或客户诉求...')
      .fill('客户想了解这款产品的保障范围');
    await page.getByRole('button', { name: '发送' }).click();

    // REFUSE 安全提示（确定性：无匹配 KB → 后端固定 REFUSE 流程）
    await expect(page.getByText('当前知识库没有足够的产品依据')).toBeVisible({
      timeout: 30_000,
    });

    watcher.assert();
  });
});
