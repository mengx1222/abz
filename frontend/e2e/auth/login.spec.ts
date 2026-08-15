import { test, expect } from '@playwright/test';

/**
 * E2E 黄金路径 1/4 — 登录（真实表单流程）
 *
 * 验证：
 *   - 打开登录页
 *   - 输入确定性 AGENT 账号 13800138000 / 888888
 *   - 提交 → 进入 /dashboard
 *   - URL、用户名、页面关键元素正确
 *   - 全程捕获 console error / pageerror（任何真实错误 → 失败）
 */
test.describe('Login 流程', () => {
  test('AGENT 账号表单登录 → Dashboard', async ({ page }) => {
    // 浏览器错误监控（任务十二）：任何 console error / 未捕获异常 → 失败
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
    });
    page.on('pageerror', (err) => {
      errors.push(`pageerror: ${err.message}`);
    });

    // 1. 打开登录页
    await page.goto('/login');
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('heading', { name: '登录' })).toBeVisible();

    // 2. 输入手机号 + 验证码
    const phoneInput = page.getByPlaceholder('请输入手机号');
    const codeInput = page.getByPlaceholder('请输入验证码');
    await phoneInput.fill('13800138000');
    await codeInput.fill('888888');

    // 3. 提交登录
    await page.getByRole('button', { name: '登录' }).click();

    // 4. 进入 Dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
    await expect(page).toHaveURL(/\/dashboard/);

    // 5. 页面关键元素出现（用户名来自 seed 的 AGENT 林思远）
    await expect(page.getByText('林思远').first()).toBeVisible({ timeout: 15_000 });

    // 6. 无真实 JS/网络错误
    expect(errors, `浏览器错误:\n${errors.join('\n')}`).toEqual([]);
  });
});
