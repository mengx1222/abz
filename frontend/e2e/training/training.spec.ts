import { test, expect } from '@playwright/test';

/**
 * E2E 阶段三 — Training（AI 陪练）
 *
 * 环境：真实 PG + Redis + 真实 AI provider（DashScope；E2E CI 已 seed 确定性训练场景）
 *
 * 覆盖：
 *   - 页面加载（场景列表 + 确定性场景可见）
 *   - 完整训练流程：选择确定性场景 → 开始训练 → SSE 消息（≥2 轮）→ 完成 → 评分/反馈可见
 *
 * 浏览器监控：console error / pageerror / API 4xx/5xx → 失败
 * 无 sleep：确定性 locator/expect/waitFor
 * 不断言固定 AI 文案（真实模型有随机性）：只验证非空 / 状态 / score / 页面成功
 */
test.describe('Training（AI 陪练）', () => {
  function watchPage(page: import('@playwright/test').Page) {
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

  // seed.py 内置确定性场景（幂等写入 DB）
  const DETERMINISTIC_SCENARIO = '"太贵了" — 重疾险价格犹豫';

  test('页面加载：AI陪练页 + 确定性场景列表可见', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/training');

    await expect(page.getByRole('heading', { name: 'AI陪练' })).toBeVisible({ timeout: 15_000 });
    // 确定性场景（seed 内置）
    const scenario = page.getByText(DETERMINISTIC_SCENARIO).first();
    await expect(scenario).toBeVisible({ timeout: 15_000 });
    // 每个场景卡片有「开始训练」按钮
    await expect(page.getByRole('button', { name: '开始训练' }).first()).toBeVisible();

    watcher.assert();
  });

  test('完整训练：确定性场景 → 开始训练 → SSE ≥2 轮 → 完成 → 评分/反馈可见', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/training');

    // 确定性场景（seed 内置）所在卡片内的「开始训练」按钮
    // （场景列表按 created_at desc 排序，不能用 first() 假设顺序）
    const startBtn = page
      .getByText(DETERMINISTIC_SCENARIO)
      .first()
      .locator('xpath=ancestor::div[contains(@class, "bg-card")][1]//button[contains(., "开始训练")]');
    await expect(startBtn).toBeVisible({ timeout: 15_000 });
    await startBtn.click();

    // 进入对话页：scenario 标题可见（会话自动创建）
    await expect(page.getByRole('heading', { name: DETERMINISTIC_SCENARIO })).toBeVisible({ timeout: 20_000 });
    const input = page.getByPlaceholder('输入您的销售话术...');
    await expect(input).toBeVisible({ timeout: 20_000 });

    // 发送 ≥2 轮消息（每轮：agent 消息 → customer SSE 流式回复非空）
    const rounds = [
      '您好，我了解您对保费有些顾虑，能说说主要担心什么吗？',
      '我理解您的想法，保费是长期投入，但保障是应对风险的关键，我们可以看看更合适的方案。',
    ];
    for (const round of rounds) {
      await input.fill(round);
      await page.getByRole('button', { name: '发送' }).click();
      // 等待 customer 回复非空（SSE token 流式完成；不依赖具体文案）
      // 消息气泡均为 span.whitespace-pre-wrap，最新一条即当前 customer 流式内容
      const lastBubble = page.locator('span.whitespace-pre-wrap').last();
      await expect(lastBubble).not.toBeEmpty({ timeout: 60_000 });
    }

    // 至少存在 2 条 agent 消息（'我' 头像，justify-end）—— 证明 2 轮已发送
    const agentMessages = page.locator('div.justify-end');
    expect(await agentMessages.count()).toBeGreaterThanOrEqual(2);

    // 结束训练 · 查看评分
    const completeBtn = page.getByRole('button', { name: /结束训练/ });
    await expect(completeBtn).toBeEnabled({ timeout: 20_000 });
    await completeBtn.click();

    // 评分区出现（SSE scoring 完成）
    await expect(page.getByText('训练评分', { exact: true })).toBeVisible({ timeout: 90_000 });
    // 综合评分数字可见（text-3xl 分数值，0-100，非空）
    const scoreValue = page.locator('div.text-3xl.font-bold').first();
    await expect(scoreValue).not.toBeEmpty({ timeout: 20_000 });
    // 评分维度标签（精确匹配，避免与评分流式文本「生成综合评分报告」混淆）
    await expect(page.getByText('产品准确性', { exact: true })).toBeVisible({ timeout: 20_000 });
    // 反馈区（优势/待提升/建议）至少存在一项
    const feedback = page.getByText(/优势|待提升|建议/).first();
    await expect(feedback).toBeVisible({ timeout: 20_000 });

    watcher.assert();
  });
});
