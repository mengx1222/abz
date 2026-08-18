import { test, expect } from '@playwright/test';

/**
 * E2E — 知识库管理（Knowledge Admin Production 对接，Task 23）
 *
 * 环境：真实 PG + Redis + mock/real AI provider（CI，DEMO_MODE=false）
 * 数据：e2e_seed_knowledge.py 幂等创建 KB「E2E产品知识库」+ 2 文档（org=NULL 共享，全员可见）
 *
 * 覆盖（最小 Admin 流程）：
 *   - K-1 知识库列表加载（production API：真实 DB-backed 数据渲染）
 *   - K-2 文档列表（点击知识库 → 文档列表渲染）
 *   - K-3 文档详情（点击文档 → 详情视图元信息渲染）
 *
 * 浏览器监控：console error / pageerror / API 4xx/5xx → 失败
 */
test.describe('知识库管理（Knowledge Admin）', () => {
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

  test('K-1 知识库列表加载（production API）', async ({ page }) => {
    const watcher = watchPage(page);
    // 诊断：捕获 KB list API 响应状态
    const kbResp = page.waitForResponse(
      (r) => r.url().includes('/admin/knowledge-bases') && r.request().method() === 'GET',
      { timeout: 20_000 },
    ).catch(() => null);
    await page.goto('/knowledge');

    // 页面标题
    await expect(page.getByRole('heading', { name: '知识库管理' })).toBeVisible({ timeout: 15_000 });

    const resp = await kbResp;
    if (resp) {
      console.log('DIAG KB list API status:', resp.status());
      const body = await resp.json().catch(() => null);
      console.log('DIAG KB list body keys:', body ? Object.keys(body) : 'null');
      if (body && Array.isArray(body.data)) {
        console.log('DIAG KB list count:', body.data.length);
        console.log('DIAG KB names:', body.data.map((kb: { name: string }) => kb.name));
      }
    } else {
      console.log('DIAG KB list API: no response captured');
    }

    // 诊断：等待 React 渲染后打印页面正文与错误
    await page.waitForTimeout(3_000);
    const bodyText = await page.locator('body').innerText().catch(() => '');
    console.log('DIAG body text:', bodyText.slice(0, 2000).replace(/\n/g, ' | '));
    console.log('DIAG page errors:', JSON.stringify(watcher.errors));
    console.log('DIAG api errors:', JSON.stringify(watcher.apiErrors));

    // E2E seed 知识库可见（production 模式 DB-backed list）
    await expect(page.getByText('E2E产品知识库')).toBeVisible({ timeout: 15_000 });

    watcher.assert();
  });

  test('K-2 文档列表（点击知识库进入）', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/knowledge');

    await expect(page.getByText('E2E产品知识库')).toBeVisible({ timeout: 15_000 });
    await page.getByText('E2E产品知识库').click();

    // seed 文档渲染（production API list）
    await expect(page.getByText('安诊保百万医疗险产品手册')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('安诊保重疾险产品手册')).toBeVisible();

    watcher.assert();
  });

  test('K-3 文档详情（元信息视图）', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/knowledge');

    await expect(page.getByText('E2E产品知识库')).toBeVisible({ timeout: 15_000 });
    await page.getByText('E2E产品知识库').click();
    await expect(page.getByText('安诊保百万医疗险产品手册')).toBeVisible({ timeout: 15_000 });
    await page.getByText('安诊保百万医疗险产品手册').click();

    // 详情视图（production API detail）：元信息面板渲染，不崩溃
    await expect(page.getByText('文件名')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('文件类型')).toBeVisible();
    await expect(page.getByText('知识块数')).toBeVisible();

    watcher.assert();
  });
});
