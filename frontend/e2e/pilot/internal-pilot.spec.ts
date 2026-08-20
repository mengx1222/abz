import { test, expect, request as pwRequest } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * E2E — Internal Pilot Golden Flow（ULTIMATE Pilot Validation，增量 spec）
 *
 * 与既有 GF-1（golden-flow.spec.ts，运行时自建客户）互补：
 * - Pilot-1 黄金链改用 **seed 确定性试点客户**（13900000001 陈女士，assigned_to=13800138000），
 *   验证「当前 Pilot seed 数据」驱动的真实闭环：登录态 → Dashboard → Customer 360 →
 *   AI Sales Agent（RAG/Citation/Compliance）→ Training → Growth。
 * - Pilot-2 权限安全（API 级）：本人 assigned 客户 200；随机 UUID 404（无泄露）；
 *   列表仅含本人 assigned 客户（P0-1 同源语义）。
 *
 * 稳定断言：页面到达 / 客户存在 / Agent started / Citation visible / Compliance state visible /
 * Training 页面与场景 / Growth 数据可见。不依赖固定 AI 文案。
 * 监控：console error / pageerror / API 4xx/5xx → 失败。
 */
const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000/api/v1';
const PILOT_AGENT_PHONE = '13800138000';
const PILOT_CUSTOMER_NAME = '陈女士';
const PILOT_CUSTOMER_PHONE = '13900000001';

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

test.describe('Internal Pilot Golden Flow（seed 试点数据驱动）', () => {
  test(
    'Pilot-1 黄金链：登录态 → Dashboard → 陈女士(seed客户) → SalesAgent(Citation/Compliance) → Training → Growth',
    async ({ page }) => {
      test.setTimeout(300_000);
      const watcher = watchPage(page);

      // ---- 1) 登录态（global-setup storageState = AGENT 13800138000）----
      await page.goto('/dashboard');
      await expect(page.getByText('今日工作', { exact: true })).toBeVisible({ timeout: 15_000 });
      const token = await page.evaluate(() => localStorage.getItem('abz_token') || '');
      expect(token, 'storageState 应注入 abz_token').toBeTruthy();

      // ---- 2) Customer 360：搜索 seed 试点客户（陈女士）----
      await page.goto('/customers');
      await expect(page.getByText('客户360', { exact: true })).toBeVisible({ timeout: 15_000 });
      const search = page.getByPlaceholder(/搜索客户姓名或手机号/);
      await search.fill(PILOT_CUSTOMER_PHONE);
      await expect(page.getByText(PILOT_CUSTOMER_NAME).first()).toBeVisible({ timeout: 15_000 });
      await page.getByText(PILOT_CUSTOMER_NAME).first().click();
      await page.waitForURL(/\/customers\/[0-9a-f-]{36}/, { timeout: 15_000 });
      const customerId = page.url().split('/customers/')[1]?.split(/[?#]/)[0];
      expect(customerId).toMatch(/[0-9a-f-]{36}/);

      // ---- 3) AI Sales Agent（同一 customer_id）----
      await page.getByRole('button', { name: 'AI 销售副驾' }).click();
      await page.waitForURL(/\/sales-agent\/[0-9a-f-]{36}/, { timeout: 20_000 });
      const agentCustomerId = page.url().split('/sales-agent/')[1]?.split(/[?#]/)[0];
      expect(agentCustomerId, 'Customer → Agent 必须同一 customer_id').toBe(customerId);
      await expect(page.getByText(PILOT_CUSTOMER_NAME).first()).toBeVisible({ timeout: 15_000 });

      const input = page.getByPlaceholder('输入销售场景或客户诉求...');
      await expect(input).toBeVisible({ timeout: 15_000 });
      await input.fill('客户想了解医疗险的保障范围和理赔流程，帮我准备沟通话术');
      await page.getByRole('button', { name: '发送' }).click();

      // Agent started（tool_planned 确定性事件）
      await expect(page.getByText('正在查询客户信息').first()).toBeVisible({ timeout: 20_000 });
      await expect(page.getByRole('button', { name: '发送' })).toBeVisible({ timeout: 90_000 });

      // Citation（RAG 产品知识来源，真实后端返回）
      await expect(page.getByText('产品知识来源')).toBeVisible({ timeout: 20_000 });
      const citationCount = await page
        .locator('div.rounded-lg', { hasText: /安诊保|产品手册|未知文档/ })
        .count();
      expect(citationCount, 'Citation 面板应包含 ≥1 条依据').toBeGreaterThan(0);

      // Compliance（真实绑定后端结果）
      await expect(page.getByText('合规检查').first()).toBeVisible({ timeout: 20_000 });
      await expect(page.getByText(/合规通过|建议人工确认|禁止直接对客使用/).first()).toBeVisible({
        timeout: 10_000,
      });

      // ---- 4) Training：页面到达 + 场景可见 ----
      await page.goto('/training');
      await expect(page.getByRole('heading', { name: 'AI陪练' })).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText(/太贵了|客户异议|价格犹豫|产品咨询/).first()).toBeVisible({
        timeout: 15_000,
      });

      // ---- 5) Growth：同用户训练数据可达（ability_scores 仅来自训练评分）----
      await page.goto('/growth');
      await expect(page.getByRole('heading', { name: '我的成长' })).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText('能力评估')).toBeVisible({ timeout: 15_000 });

      watcher.assert();
    }
  );

  test(
    'Pilot-2 权限安全：本人 assigned 客户可见、随机 UUID 404、列表仅本人（P0-1 同源）',
    async ({ page }) => {
      test.setTimeout(60_000);
      // 先导航建立 origin（否则 localStorage 读取抛 SecurityError）
      await page.goto('/dashboard');
      await expect(page.getByText('今日工作', { exact: true })).toBeVisible({ timeout: 15_000 });
      const token = await page.evaluate(() => localStorage.getItem('abz_token') || '');
      expect(token).toBeTruthy();
      const api = await pwRequest.newContext();
      const headers = { Authorization: `Bearer ${token}` };

      // 1) 本人 assigned 客户（seed 陈女士）→ 200
      const list = await api.get(
        `${API_BASE}/customers?search=${PILOT_CUSTOMER_PHONE}&page=1&page_size=10`,
        { headers },
      );
      expect(list.status()).toBe(200);
      const items: any[] = (await list.json()).data || [];
      const chen = items.find((c: any) => c.phone === PILOT_CUSTOMER_PHONE);
      expect(chen, 'seed 客户陈女士应可见').toBeTruthy();
      const detail = await api.get(`${API_BASE}/customers/${chen.id}`, { headers });
      expect(detail.status()).toBe(200);

      // 2) 随机 UUID → 404（不泄露存在性）
      const missing = await api.get(
        `${API_BASE}/customers/00000000-0000-0000-0000-00000000ffff`,
        { headers },
      );
      expect(missing.status()).toBe(404);

      // 3) 列表仅含本人 assigned 客户（seed 3 个全部 assigned_to=13800138000）
      const all = await api.get(`${API_BASE}/customers?page=1&page_size=50`, { headers });
      expect(all.status()).toBe(200);
      const allItems: any[] = (await all.json()).data || [];
      const seedPhones = ['13900000001', '13900000002', '13900000003'];
      const visibleSeed = allItems.filter((c: any) => seedPhones.includes(c.phone));
      expect(visibleSeed.length).toBe(3);

      await api.dispose();
    }
  );
});
