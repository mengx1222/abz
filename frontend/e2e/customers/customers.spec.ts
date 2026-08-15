import { test, expect } from '@playwright/test';

/**
 * E2E 黄金路径 3/4 — 客户列表
 *
 * 验证（storageState 已登录）：
 *   - 客户 360 页加载
 *   - 确定性客户 E2E-张先生 出现
 *   - 搜索/筛选基础操作（按手机号搜索）
 *   - 客户表格/卡片渲染
 *   - 无 console error / pageerror / API 500
 */
test.describe('客户列表', () => {
  test('客户列表加载 + 确定性客户可见 + 搜索', async ({ page }) => {
    const errors: string[] = [];
    const apiErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
    });
    page.on('pageerror', (err) => {
      errors.push(`pageerror: ${err.message}`);
    });
    page.on('response', (res) => {
      if (res.url().includes('/api/v1/customers') && res.status() >= 400) {
        apiErrors.push(`API ${res.status()} ${res.url()}`);
      }
    });

    await page.goto('/customers');

    // 页面标题
    await expect(page.getByText('客户360', { exact: true })).toBeVisible({ timeout: 15_000 });

    // 确定性测试客户出现（global-setup 幂等创建）
    await expect(page.getByText('E2E-张先生').first()).toBeVisible({ timeout: 15_000 });

    // 搜索基础操作：按手机号过滤
    const search = page.getByPlaceholder(/搜索客户姓名或手机号/);
    await search.fill('13900001111');
    // 等待确定性客户仍可见（搜索结果）
    await expect(page.getByText('E2E-张先生').first()).toBeVisible({ timeout: 15_000 });

    // 无真实错误
    expect(apiErrors, `API 错误:\n${apiErrors.join('\n')}`).toEqual([]);
    expect(errors, `浏览器错误:\n${errors.join('\n')}`).toEqual([]);
  });
});
