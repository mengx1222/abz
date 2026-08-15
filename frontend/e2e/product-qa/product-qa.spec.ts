import { test, expect } from '@playwright/test';

/**
 * E2E 第二阶段 — Product QA（AI 产品专家）
 *
 * 环境：真实 PG + Redis + 真实 AI provider（DashScope；RAG 语义检索命中确定性知识库）
 *
 * 覆盖：
 *   - 页面加载（输入框/提交按钮/无错误）
 *   - 真实产品问答（知识库有依据 → SSE 流式 → 回答完成）
 *   - Citation（参考来源出现）
 *   - RAG Refusal（知识库无依据 → 不伪造来源引用）
 *
 * 浏览器监控：console error / pageerror / API 4xx/5xx → 失败
 * 无 sleep：确定性 locator/expect/waitFor
 */
test.describe('Product QA', () => {
  // 收集浏览器/API 错误（复用 Task 11 模式）
  function watchPage(page: import('@playwright/test').Page) {
    const errors: string[] = [];
    const apiErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
    });
    page.on('pageerror', (err) => {
      errors.push(`pageerror: ${err.message}`);
    });
    page.on('response', (res) => {
      if (res.url().includes('/api/v1/') && res.status() >= 400) {
        apiErrors.push(`API ${res.status()} ${res.url()}`);
      }
    });
    return { errors, apiErrors, assert: () => {
      expect(apiErrors, `API 错误:\n${apiErrors.join('\n')}`).toEqual([]);
      expect(errors, `浏览器错误:\n${errors.join('\n')}`).toEqual([]);
    } };
  }

  test('页面加载：输入框 + 发送按钮 + 无错误', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/product-qa');

    await expect(page.locator('h1', { hasText: 'AI 产品专家' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByPlaceholder('输入你的保险问题...')).toBeVisible();
    await expect(page.getByRole('button', { name: '发送' })).toBeVisible();
    // 初始引导文案
    await expect(page.getByText(/我是安诊保 AI 产品专家/)).toBeVisible();

    watcher.assert();
  });

  test('真实问答：知识库有依据 → SSE 流式回答完成', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/product-qa');

    const input = page.getByPlaceholder('输入你的保险问题...');
    // 知识库确定性文档明确包含"医疗险"、"保障范围"、"等待期"、"免赔额"
    await input.fill('介绍一下医疗险的保障范围和等待期');
    await page.getByRole('button', { name: '发送' }).click();

    // 等待助手回答非空（SSE token 流式渲染完成）
    const assistant = page.locator('div.whitespace-pre-wrap');
    await expect(assistant.last()).not.toBeEmpty({ timeout: 30_000 });

    // 回答内容不应为空字符串
    const content = await assistant.last().textContent();
    expect(content?.trim().length).toBeGreaterThan(0);

    watcher.assert();
  });

  test('Citation：回答附带参考来源', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/product-qa');

    const input = page.getByPlaceholder('输入你的保险问题...');
    await input.fill('安诊保百万医疗险的理赔流程是什么');
    await page.getByRole('button', { name: '发送' }).click();

    // 参考来源区块出现（RAG 命中知识库 → 前端渲染 sources）
    const sourcesHeading = page.getByText('📖 参考来源');
    await expect(sourcesHeading).toBeVisible({ timeout: 30_000 });

    // 至少一个来源 title（知识库文档名）
    await expect(page.getByText('安诊保百万医疗险产品手册').first()).toBeVisible({ timeout: 10_000 });

    watcher.assert();
  });

  test('RAG Refusal：知识库无依据 → 不伪造参考来源', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/product-qa');

    const input = page.getByPlaceholder('输入你的保险问题...');
    // "极光量子保险" 不在 E2E 确定性知识库中（RAG 无命中）
    await input.fill('极光量子保险的承保范围是什么');
    await page.getByRole('button', { name: '发送' }).click();

    // 等待回答流程结束（assistant 消息出现且不再处于 loading）
    const assistant = page.locator('div.whitespace-pre-wrap');
    await expect(assistant.last()).not.toBeEmpty({ timeout: 30_000 });
    await expect(assistant.last().locator('span.animate-pulse')).toHaveCount(0, { timeout: 30_000 });

    // 知识库无依据 → 不显示"参考来源"区（拒绝伪造 citation）
    const sourcesHeading = page.getByText('📖 参考来源');
    await expect(sourcesHeading).toHaveCount(0, { timeout: 10_000 });

    watcher.assert();
  });
});
