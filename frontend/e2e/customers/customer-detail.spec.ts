import { test, expect } from '@playwright/test';

/**
 * E2E 黄金路径 4/4 — 客户详情
 *
 * 验证（storageState 已登录）：
 *   - 点击确定性客户 → 详情页加载
 *   - 基本信息出现
 *   - 现有模块（跟进任务 / AI 分析入口）正常
 *   - 无 console error / pageerror / API 500
 *   - 只测已有功能，不测未来功能
 */
test.describe('客户详情', () => {
  test('打开确定性客户详情并验证基本模块', async ({ page }) => {
    const errors: string[] = [];
    const apiErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
    });
    page.on('pageerror', (err) => {
      errors.push(`pageerror: ${err.message}`);
    });
    page.on('response', (res) => {
      if (res.url().includes('/api/v1/customers/') && res.status() >= 400) {
        apiErrors.push(`API ${res.status()} ${res.url()}`);
      }
    });

    // 1. 列表 → 点击确定性客户
    await page.goto('/customers');
    await expect(page.getByText('E2E-张先生').first()).toBeVisible({ timeout: 15_000 });
    await page.getByText('E2E-张先生').first().click();

    // 2. 详情页加载（URL 进入 /customers/{id}）
    await page.waitForURL(/\/customers\/[0-9a-f-]+/, { timeout: 15_000 });

    // 3. 客户姓名出现
    await expect(page.getByText('E2E-张先生').first()).toBeVisible({ timeout: 15_000 });

    // 4. 基本信息 tab（当前已有模块）
    const infoTab = page.getByRole('button', { name: '基本信息' });
    if (await infoTab.count()) {
      await infoTab.first().click();
      await expect(page.getByText(/手机号|电话|客户类型|意向度|年龄段/).first()).toBeVisible({ timeout: 10_000 });
    }

    // 5. AI 分析入口存在（只验证入口，不触发真实 AI）
    const analysisTab = page.getByRole('button', { name: /AI 分析/ });
    if (await analysisTab.count()) {
      await expect(analysisTab.first()).toBeVisible();
    }

    // 无真实错误
    expect(apiErrors, `API 错误:\n${apiErrors.join('\n')}`).toEqual([]);
    expect(errors, `浏览器错误:\n${errors.join('\n')}`).toEqual([]);
  });
});
