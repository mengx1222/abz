import { test, expect } from '@playwright/test';

/**
 * E2E 黄金路径 2/4 — Dashboard 工作台
 *
 * 验证（storageState 已登录）：
 *   - Dashboard 真正渲染成功（非 HTTP 200 判断）
 *   - 核心统计卡片出现（今日工作 / AI 今日建议）
 *   - 无 console error / pageerror
 *   - 无空白（关键区块可见）
 */
test.describe('Dashboard 工作台', () => {
  test('登录态加载 Dashboard 且核心卡片渲染', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
    });
    page.on('pageerror', (err) => {
      errors.push(`pageerror: ${err.message}`);
    });

    await page.goto('/dashboard');

    // 标题区：问候语 + 用户名（渲染成功的直接证据）
    await expect(page.locator('h1')).toBeVisible({ timeout: 15_000 });

    // 核心统计卡片（今日工作 / AI 今日建议至少出现一个区块标题）
    const statHeading = page.getByText('今日工作', { exact: true });
    const aiHeading = page.getByText('AI 今日建议', { exact: true });
    await expect(statHeading.or(aiHeading).first()).toBeVisible({ timeout: 15_000 });

    // 页面非空白：至少有一个统计 Card 渲染（data 非空时）
    const statCards = page.locator('main').locator('[class*="rounded"]').first();
    await expect(statCards).toBeVisible();

    // 无真实错误
    expect(errors, `浏览器错误:\n${errors.join('\n')}`).toEqual([]);
  });
});
