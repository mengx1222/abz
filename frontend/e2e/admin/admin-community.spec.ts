import { test, expect, request as pwRequest } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * E2E — Admin 社区管理（Task 25 最小 Admin 流程）
 *
 * 环境：真实 PG + Redis + mock/real AI provider（CI，DEMO_MODE=false）
 * 账号：SYSTEM_ADMIN 13800138003 / 888888（seed.py 固定；管理端点 require_role
 *       SYSTEM_ADMIN/HQ_ADMIN/BRANCH_ADMIN，AGENT 无权 —— 需独立登录注入 storage）
 * 数据：admin 管理 API 为 Demo-only（_DEMO_ADMIN_POSTS，production 后端下仍返回
 *       确定性 demo 数据）→ 列表断言用固定标题「我是如何用3句话让客户理解免赔额的」
 *
 * 覆盖（最小 Admin 关键路径）：
 *   - A-1 列表加载：登录 SYSTEM_ADMIN → /admin/community → 帖子渲染（无浏览器/API 错误）
 *   - A-2 置顶操作：置顶 toggle → toast 反馈 → 恢复（验证 mutation + UI 反馈闭环）
 *
 * 浏览器监控：console error / pageerror / API 4xx/5xx → 失败
 */
const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000/api/v1';

async function loginAsSystemAdmin(): Promise<{
  token: string;
  user: Record<string, unknown>;
}> {
  const api = await pwRequest.newContext({ baseURL: API_BASE });
  const res = await api.post('/auth/login', {
    data: { phone: '13800138003', password: '888888' },
  });
  if (res.status() !== 200) {
    throw new Error(`admin login failed: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  const token = body.data.access_token;
  const me = await api.get('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  });
  const user = (await me.json()).data as Record<string, unknown>;
  await api.dispose();
  return { token, user };
}

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

test.describe('Admin 社区管理（SYSTEM_ADMIN）', () => {
  test('A-1 列表加载（production 后端 demo 数据渲染）', async ({ page }) => {
    const watcher = watchPage(page);
    const { token, user } = await loginAsSystemAdmin();

    await page.addInitScript(
      ([t, u]) => {
        localStorage.setItem('abz_token', t);
        localStorage.setItem('abz_user', JSON.stringify(u));
      },
      [token, user] as [string, Record<string, unknown>]
    );

    await page.goto('/admin/community');

    // 页面标题
    await expect(page.getByRole('heading', { name: '社区管理' })).toBeVisible({
      timeout: 15_000,
    });

    // 确定性 demo 帖子渲染（admin API 生产后端下返回固定 demo 数据）
    await expect(
      page.getByText('我是如何用3句话让客户理解免赔额的')
    ).toBeVisible({ timeout: 15_000 });

    watcher.assert();
  });

  test('A-2 置顶/取消置顶操作反馈', async ({ page }) => {
    const watcher = watchPage(page);
    const { token, user } = await loginAsSystemAdmin();

    await page.addInitScript(
      ([t, u]) => {
        localStorage.setItem('abz_token', t);
        localStorage.setItem('abz_user', JSON.stringify(u));
      },
      [token, user] as [string, Record<string, unknown>]
    );

    await page.goto('/admin/community');
    await expect(page.getByText('我是如何用3句话让客户理解免赔额的')).toBeVisible({
      timeout: 15_000,
    });

    const row = page.locator('tbody tr').first();

    // demo 帖子初始 is_pinned=true → 先取消置顶
    await row.locator('button[title="取消置顶"]').click();
    await expect(page.getByText(/已取消置顶/)).toBeVisible({ timeout: 10_000 });

    // 刷新后恢复置顶（验证 toggle 闭环）
    await row.locator('button[title="置顶"]').click();
    await expect(page.getByText(/已置顶/)).toBeVisible({ timeout: 10_000 });

    watcher.assert();
  });
});
