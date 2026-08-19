import { test, expect, request as pwRequest } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * E2E — Golden Business Flow（Task 29 完整销售准备黄金链）
 *
 * 一条真实浏览器链路，证明一个代理人可以完成一次完整的「销售准备黄金流程」：
 *   登录 → Dashboard → Customer 360 → AI Sales Agent（客户上下文 → 产品知识/RAG →
 *   Citation → 销售建议/话术 → Compliance）→ Training（陪练 ≥2 轮 + 评分）→
 *   Growth（训练数据/能力评估出现）
 *
 * 环境：真实 PG + Redis + backend（DEMO_MODE=false）+ 真实 AI provider（CI Secrets；
 *        无 key 时 e2e-playwright workflow 回退 mock —— 真实 AI 完整链由
 *        real-ai-smoke.yml Phase 11 显式验证）
 * 账号：AGENT 13800138000（global-setup storageState，seed 固定）
 * 客户：确定性客户 E2E-黄金链客户 / 13900002222（幂等创建+更新 insurance_type=医疗险，
 *       保证 RAG 命中 E2E产品知识库 → Citation 出现）
 * 知识库：e2e_seed_knowledge.py 确定性「E2E产品知识库」（医疗险 ≥3 chunk → Confidence HIGH）
 *
 * 数据连续性（跨模块同用户/同客户）：
 *   - 同一 AGENT 用户贯穿全程（storageState）
 *   - customer_id 从 /customers/{id} 提取，与 /sales-agent/{id} 断言一致
 *   - RAG citation 必须出现（产品知识来源面板）
 *   - Compliance 状态必须出现（合规检查面板）
 *   - Training 完成后 Growth「能力评估」出现（ability_scores 仅来自训练评分，
 *     list_training_scores(user_id) 按当前用户过滤 → 同用户数据连续）
 *   - API 断言：训练后 total_exp ≥ 训练前 + 10（count_completed_trainings × 10）
 *
 * 不依赖固定 AI 文案：只断言稳定事实（页面可见 / 状态 / 非空 / score / URL 一致）。
 * 浏览器监控：console error / pageerror / API 4xx/5xx → 失败。
 */
const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000/api/v1';
const GF_CUSTOMER_NAME = 'E2E-黄金链客户';
const GF_CUSTOMER_PHONE = '13900002222';
const GF_INSURANCE_TYPE = '医疗险';
const DETERMINISTIC_SCENARIO = '"太贵了" — 重疾险价格犹豫';

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

/** 幂等确保确定性黄金链客户（存在则更新 insurance_type，不存在则创建） */
async function ensureGoldenCustomer(token: string): Promise<string> {
  const api = await pwRequest.newContext();
  const headers = { Authorization: `Bearer ${token}` };
  // 1) 按手机号查找（确定性）
  const list = await api.get(
    `${API_BASE}/customers?search=${GF_CUSTOMER_PHONE}&page=1&page_size=10`,
    { headers },
  );
  if (list.status() !== 200) {
    throw new Error(`list customers failed: ${list.status()} ${await list.text()}`);
  }
  const items = (await list.json()).data || [];
  const existing = items.find(
    (c: any) => c.phone === GF_CUSTOMER_PHONE && c.name === GF_CUSTOMER_NAME,
  );
  if (existing) {
    // 2) 存在 → 更新 insurance_type（保证 RAG 命中医疗险 KB）
    const upd = await api.put(`${API_BASE}/customers/${existing.id}`, {
      headers,
      data: { insurance_type: GF_INSURANCE_TYPE },
    });
    if (upd.status() !== 200) {
      throw new Error(`update customer failed: ${upd.status()} ${await upd.text()}`);
    }
    await api.dispose();
    return String(existing.id);
  }
  // 3) 不存在 → 创建
  const created = await api.post(`${API_BASE}/customers`, {
    headers,
    data: {
      name: GF_CUSTOMER_NAME,
      phone: GF_CUSTOMER_PHONE,
      customer_type: 'personal',
      current_stage: 'needs_analysis',
      intention_level: 4,
      age: 38,
      gender: 'male',
      insurance_type: GF_INSURANCE_TYPE,
      note: 'Golden Flow E2E 确定性测试客户（幂等创建）',
    },
  });
  if (created.status() !== 200 && created.status() !== 201) {
    throw new Error(`create customer failed: ${created.status()} ${await created.text()}`);
  }
  const id = (await created.json()).data?.id;
  await api.dispose();
  if (!id) throw new Error('create customer: missing id');
  return String(id);
}

/** 训练前 total_exp（API 断言数据连续性基线） */
async function getGrowthTotalExp(token: string): Promise<number> {
  const api = await pwRequest.newContext();
  const res = await api.get(`${API_BASE}/growth/overview`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status() !== 200) {
    await api.dispose();
    throw new Error(`growth overview failed: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  await api.dispose();
  // growth API 用 response_model=GrowthOverview 直接返回（无 success/data 包装）
  return body.total_exp ?? 0;
}

test.describe('Golden Business Flow（完整销售准备黄金链）', () => {
  test(
    'GF-1 黄金链：Dashboard → Customer360 → SalesAgent(RAG/Citation/Compliance) → Training(评分) → Growth(数据连续)',
    async ({ page }) => {
      // 完整链（Agent 黄金链 + Training 2 轮 + 评分 + Growth）执行较长 → 5min
      test.setTimeout(300_000);
      const watcher = watchPage(page);

      // ---- 0) 登录态（storageState=AGENT）+ 确定性客户准备 ----
      await page.goto('/dashboard');
      await expect(page.getByText('今日工作', { exact: true })).toBeVisible({ timeout: 15_000 });
      const token = await page.evaluate(() => localStorage.getItem('abz_token') || '');
      expect(token, 'storageState 应注入 abz_token').toBeTruthy();

      const baselineExp = await getGrowthTotalExp(token);
      const customerId = await ensureGoldenCustomer(token);

      // ---- 1) Customer 360：搜索确定性客户并打开详情 ----
      await page.goto('/customers');
      await expect(page.getByText('客户360', { exact: true })).toBeVisible({ timeout: 15_000 });
      const search = page.getByPlaceholder(/搜索客户姓名或手机号/);
      await search.fill(GF_CUSTOMER_PHONE);
      await expect(page.getByText(GF_CUSTOMER_NAME).first()).toBeVisible({ timeout: 15_000 });
      await page.getByText(GF_CUSTOMER_NAME).first().click();
      await expect(page.getByText(GF_CUSTOMER_NAME).first()).toBeVisible({ timeout: 15_000 });

      // 同一 customer_id：从 Customer Detail URL 提取
      await page.waitForURL(/\/customers\/[0-9a-f-]{36}/, { timeout: 15_000 });
      const detailUrlCustomerId = page.url().split('/customers/')[1]?.split(/[?#]/)[0];
      expect(detailUrlCustomerId).toBe(customerId);

      // ---- 2) AI Sales Agent：客户详情 → 销售副驾（同一 customer_id） ----
      await page.getByRole('button', { name: 'AI 销售副驾' }).click();
      await page.waitForURL(/\/sales-agent\/[0-9a-f-]{36}/, { timeout: 20_000 });
      const agentUrlCustomerId = page.url().split('/sales-agent/')[1]?.split(/[?#]/)[0];
      expect(agentUrlCustomerId, 'Customer → Agent 必须同一 customer_id').toBe(customerId);

      // 客户上下文（最小字段渲染）
      await expect(page.getByText(GF_CUSTOMER_NAME).first()).toBeVisible({ timeout: 15_000 });

      // ---- 3) 发起真实销售目标 → SSE 流式执行 ----
      const input = page.getByPlaceholder('输入销售场景或客户诉求...');
      await expect(input).toBeVisible({ timeout: 15_000 });
      await input.fill('客户想了解医疗险的保障范围和理赔流程，帮我准备沟通话术');
      await page.getByRole('button', { name: '发送' }).click();

      // 安全执行状态（tool_planned 确定性事件；气泡+左卡两处 → .first()）
      await expect(page.getByText('正在查询客户信息').first()).toBeVisible({ timeout: 20_000 });

      // 最终结果非空：等发送按钮恢复（isStreaming 结束）
      await expect(page.getByRole('button', { name: '发送' })).toBeVisible({ timeout: 90_000 });

      // ---- 4) Citation（RAG 产品知识来源，真实后端返回） ----
      await expect(page.getByText('产品知识来源')).toBeVisible({ timeout: 20_000 });
      // 至少一条 citation（document_title 非空 —— 不依赖具体标题）
      const citationCount = await page
        .locator('div.rounded-lg', { hasText: /安诊保|产品手册|未知文档/ })
        .count();
      expect(citationCount, 'Citation 面板应包含 ≥1 条依据').toBeGreaterThan(0);

      // ---- 5) Compliance（真实绑定后端结果，GREEN/YELLOW/RED 任一） ----
      // '合规检查' 出现在 header 副标题 + 每条 assistant 消息的合规面板（span + GREEN hint）
      // → 多元素正常（多轮对话每条消息都有合规面板），用 .first() 取首个面板
      await expect(page.getByText('合规检查').first()).toBeVisible({ timeout: 20_000 });
      await expect(page.getByText(/合规通过|建议人工确认|禁止直接对客使用/).first()).toBeVisible({
        timeout: 10_000,
      });

      // ---- 6) Training：确定性场景 → ≥2 轮 → 结束 → 评分 ----
      await page.goto('/training');
      await expect(page.getByRole('heading', { name: 'AI陪练' })).toBeVisible({ timeout: 15_000 });
      const startBtn = page
        .getByText(DETERMINISTIC_SCENARIO)
        .first()
        .locator('xpath=ancestor::div[contains(@class, "bg-card")][1]//button[contains(., "开始训练")]');
      await expect(startBtn).toBeVisible({ timeout: 15_000 });
      await startBtn.click();

      await expect(page.getByRole('heading', { name: DETERMINISTIC_SCENARIO })).toBeVisible({
        timeout: 20_000,
      });
      const tInput = page.getByPlaceholder('输入您的销售话术...');
      await expect(tInput).toBeVisible({ timeout: 20_000 });

      const rounds = [
        '您好，我了解您对保费有些顾虑，能说说主要担心什么吗？',
        '我理解您的想法，保费是长期投入，但保障是应对风险的关键，我们可以看看更合适的方案。',
      ];
      for (const round of rounds) {
        await tInput.fill(round);
        await page.getByRole('button', { name: '发送' }).click();
        const lastBubble = page.locator('span.whitespace-pre-wrap').last();
        await expect(lastBubble).not.toBeEmpty({ timeout: 60_000 });
      }
      const agentMessages = page.locator('div.justify-end');
      expect(await agentMessages.count()).toBeGreaterThanOrEqual(2);

      const completeBtn = page.getByRole('button', { name: /结束训练/ });
      await expect(completeBtn).toBeEnabled({ timeout: 20_000 });
      await completeBtn.click();
      await expect(page.getByText('训练评分', { exact: true })).toBeVisible({ timeout: 90_000 });
      const scoreValue = page.locator('div.text-3xl.font-bold').first();
      await expect(scoreValue).not.toBeEmpty({ timeout: 20_000 });

      // ---- 7) Growth：训练数据/能力评估出现（同用户数据连续） ----
      await page.goto('/growth');
      await expect(page.getByRole('heading', { name: '我的成长' })).toBeVisible({
        timeout: 15_000,
      });
      await expect(page.getByText('能力评估')).toBeVisible({ timeout: 15_000 });
      // ability_scores 仅来自训练评分（产品知识/沟通技巧/促成能力/综合表现）
      await expect(page.getByText('产品知识', { exact: true })).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText('综合表现', { exact: true })).toBeVisible();

      // API 级数据连续性：训练后 total_exp ≥ 训练前 + 10（1 次完成训练 × 10）
      const afterExp = await getGrowthTotalExp(token);
      expect(afterExp, '训练完成应使 total_exp 增加 ≥10').toBeGreaterThanOrEqual(baselineExp + 10);

      watcher.assert();
    }
  );
});
