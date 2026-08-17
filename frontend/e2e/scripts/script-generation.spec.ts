import { test, expect } from '@playwright/test';

/**
 * E2E 第二阶段 — Script Generation（AI 话术）
 *
 * 环境：真实 PG + Redis + 真实 AI provider（DashScope；E2E CI 已 seed 确定性知识库
 *       —— 含 product_type 元数据，供 RAG 产品边界过滤）
 *
 * 覆盖：
 *   - 页面加载（客户信息表单/场景/异议/风格/生成按钮）
 *   - 真实生成（确定性客户 → SSE 流式 → 至少一个话术生成成功）
 *   - Citation UI（生成结果卡片展示"产品知识依据"：文档标题/章节/来源，Task 13）
 *   - Compliance（合规徽章 GREEN/YELLOW/RED 展示）
 *   - RAG Product Boundary（错误产品 → 拒答，不展示任何产品依据，Task 13）
 *
 * 浏览器监控：console error / pageerror / API 4xx/5xx → 失败
 * 无 sleep：确定性 locator/expect/waitFor
 */
test.describe('Script Generation', () => {
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

  async function fillGenerateForm(page: import('@playwright/test').Page, opts: {
    name: string;
    product: string;
    objection?: string;
    style?: string;
  }) {
    // 客户姓名（必填）
    await page.getByPlaceholder('输入客户姓名').fill(opts.name);
    // 销售阶段
    await page.locator('select').nth(0).selectOption('needs_analysis');
    // 客户异议（可选）
    if (opts.objection) {
      await page.locator('select').nth(1).selectOption(opts.objection);
    }
    // 产品类型
    await page.locator('select').nth(2).selectOption(opts.product);
    // 风格（可选，不选则全部 4 种）
    if (opts.style) {
      await page.getByRole('button', { name: opts.style, exact: true }).click();
    }
  }

  test('页面加载：客户表单 + 场景 + 风格 + 生成按钮', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/scripts');

    await expect(page.getByRole('heading', { name: 'AI话术' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('客户信息', { exact: true })).toBeVisible();
    await expect(page.getByPlaceholder('输入客户姓名')).toBeVisible();
    await expect(page.getByText('话术风格', { exact: true })).toBeVisible();
    // 主生成按钮（页面底部 w-full primary 按钮）
    await expect(page.locator('button.w-full', { hasText: '生成话术' })).toBeVisible();

    watcher.assert();
  });

  test('真实生成：确定性客户 → SSE → 话术 + Compliance 徽章 + Citation UI', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/scripts');

    // 捕获 /scripts/generate 的 SSE 响应体（验证 rag_context/citations 字段）
    let generateBody = '';
    page.on('response', (res) => {
      if (res.url().includes('/api/v1/scripts/generate')) {
        res.text().then((t) => { generateBody += t; }).catch(() => {});
      }
    });

    // 确定性测试客户（global-setup 已创建 E2E-张先生）
    await fillGenerateForm(page, {
      name: 'E2E-张先生',
      product: '医疗险',
      objection: '太贵了',
      style: '专业型',
    });

    await page.locator('button.w-full', { hasText: '生成话术' }).click();

    // 等待生成完成提示（generation_complete 后前端显示"话术生成完成"）
    const done = page.getByText(/话术生成完成/);
    await expect(done).toBeVisible({ timeout: 60_000 });

    // 至少一个话术卡片出现（专业型），内容非空
    const scriptContent = page.locator('div.whitespace-pre-wrap').first();
    await expect(scriptContent).not.toBeEmpty({ timeout: 15_000 });

    // Compliance 徽章展示（GREEN/YELLOW/RED 之一：合规通过/建议修改/禁止使用）
    const complianceBadge = page.getByText(/合规通过|建议修改|禁止使用/).first();
    await expect(complianceBadge).toBeVisible({ timeout: 10_000 });

    // Citation UI（Task 13）：生成卡片下方出现"产品知识依据（RAG）"，且文档标题可见
    const citationHeader = page.getByText('📚 产品知识依据（RAG）');
    await expect(citationHeader).toBeVisible({ timeout: 10_000 });
    // 确定性知识库文档标题（医疗险产品手册）必须出现在依据中（同文档多 chunk 取 first）
    const docTitle = page.getByText('安诊保百万医疗险产品手册').first();
    await expect(docTitle).toBeVisible({ timeout: 10_000 });
    // 依据不为空：至少 1 个依据条目（文档标题 / 章节 / 来源可见）
    const citationItems = page.getByText(/📄/);
    expect(await citationItems.count()).toBeGreaterThan(0);

    // Citation：SSE 响应含 rag_context 事件 + citations 字段（RAG 命中知识库）
    expect(generateBody).toContain('rag_context');
    expect(generateBody).toContain('citations');

    watcher.assert();
  });

  test('RAG 产品边界：错误产品（车险）→ 拒答，不展示任何产品依据', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/scripts');

    // "车险" 在 PRODUCT_TYPES 下拉中可选，但 E2E 知识库只有医疗险/重疾险文档。
    // Task 13 产品边界：script_service 把 product_type 传入 RAG 检索 → 车险无任何
    // 知识依据 → REFUSE（不生成话术、不展示 Citation、不把医疗险/重疾险依据当车险依据）。
    await fillGenerateForm(page, {
      name: 'E2E-张先生',
      product: '车险',
      style: '专业型',
    });

    await page.locator('button.w-full', { hasText: '生成话术' }).click();

    // 生成流程结束（主按钮恢复"生成话术"可用）
    const generateBtn = page.locator('button.w-full', { hasText: '生成话术' });
    await expect(generateBtn).toBeEnabled({ timeout: 60_000 });

    // ① 错误产品不得展示任何 Citation（产品知识依据区不存在）
    await expect(page.getByText('📚 产品知识依据（RAG）')).toHaveCount(0, { timeout: 10_000 });

    // ② 不生成任何非空话术内容（REFUSE → 无产品事实性话术）
    const contents = await page.locator('div.whitespace-pre-wrap').allTextContents();
    const nonEmpty = contents.filter((t) => (t || '').trim().length > 0);
    expect(nonEmpty, `错误产品不应生成话术内容: ${JSON.stringify(contents)}`).toEqual([]);

    watcher.assert();
  });
});
