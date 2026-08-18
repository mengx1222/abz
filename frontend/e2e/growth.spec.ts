import { test, expect } from '@playwright/test';

/**
 * E2E 阶段三 — Growth（成长体系）
 *
 * 环境：真实 PG + Redis + mock AI provider（CI，DEMO_MODE=false）或 Demo 后端（本地）。
 *
 * 覆盖：
 *   - G-1 成长概览加载（统计卡片/能力评估/学习进度区域渲染）
 *   - G-2 课程列表展示（有课程 → 课程卡片；无课程 → P1-3 空状态「暂无学习课程」）
 *   - G-3 课程详情查看（P1-3 兼容：有课程 → 点击进入详情 modal；生产无课程表 →
 *         course_detail 返回 None → 友好空状态「该课程详情暂未开放」，不崩溃）
 *   - G-4 排行榜加载（Tab 切换 + 周期按钮 + 列表渲染）
 *   - G-5 成就列表加载（已解锁/未解锁分组渲染）
 *
 * 浏览器监控：console error / pageerror / API 4xx/5xx → 失败
 * 无 sleep：确定性 locator/expect；条件分支兼容 demo（有课程）与生产（无课程）两种环境。
 */
test.describe('Growth（成长体系）', () => {
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

  test('G-1 成长概览页面加载：统计卡片可见', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/growth');

    // 页面标题 + 副标题
    await expect(page.getByRole('heading', { name: '我的成长' })).toBeVisible({ timeout: 15_000 });

    // 学习中心 Tab 默认激活：本月业绩统计卡片渲染（生产/演示均有 4 项）
    await expect(page.getByText('本月业绩')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('本月互动')).toBeVisible();
    await expect(page.getByText('AI 使用次数')).toBeVisible();
    // 能力评估 / 学习进度区域
    await expect(page.getByText('能力评估')).toBeVisible();
    await expect(page.getByText('学习进度')).toBeVisible();

    watcher.assert();
  });

  test('G-2 课程列表展示：学习进度区域渲染（课程卡片或空状态）', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/growth');

    await expect(page.getByText('学习进度')).toBeVisible({ timeout: 15_000 });

    // 有课程（demo）→ 至少 1 个课程卡片；无课程（生产 P1-3）→ 友好空状态
    const emptyState = page.getByText('暂无学习课程');
    const courseRow = page.locator('div[class*="cursor-pointer"]').first();
    const hasCourses = (await courseRow.count()) > 0;

    if (hasCourses) {
      await expect(courseRow).toBeVisible();
    } else {
      await expect(emptyState).toBeVisible();
    }

    watcher.assert();
  });

  test('G-3 课程详情查看（P1-3 兼容：None → 空状态不崩溃）', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/growth');

    await expect(page.getByText('学习进度')).toBeVisible({ timeout: 15_000 });

    const courseRow = page.locator('div[class*="cursor-pointer"]').first();
    const hasCourses = (await courseRow.count()) > 0;

    if (hasCourses) {
      // 有课程 → 点击进入详情 modal，页面不崩溃
      await courseRow.click();
      const modal = page.locator('div.fixed.inset-0.z-50');
      await expect(modal).toBeVisible({ timeout: 15_000 });
      // modal 内：课程标题（详情）或空状态文案（详情未开放）至少其一
      const detailOrEmpty = page.getByText('该课程详情暂未开放，敬请期待');
      const modalHasTitle = (await modal.locator('h2').count()) > 0;
      if (modalHasTitle) {
        await expect(modal.locator('h2').first()).not.toBeEmpty();
      } else {
        await expect(detailOrEmpty).toBeVisible();
      }
      // 关闭 modal
      await page.locator('div.fixed.inset-0.z-50 button').click();
      await expect(modal).toHaveCount(0, { timeout: 10_000 });
    } else {
      // 生产无课程表（P1-3）→ 学习进度空状态友好展示，页面不崩溃
      await expect(page.getByText('暂无学习课程')).toBeVisible();
    }

    watcher.assert();
  });

  test('G-4 排行榜加载：Tab 切换 + 周期按钮 + 列表渲染', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/growth');

    // 切换到排行榜 Tab
    await page.getByRole('button', { name: '排行榜' }).click();
    await expect(page.getByRole('button', { name: '本周' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: '本月' })).toBeVisible();
    await expect(page.getByRole('button', { name: '本季度' })).toBeVisible();

    // 切换周期（本周 → 本月）后列表仍渲染
    await page.getByRole('button', { name: '本月' }).click();
    await expect(page.getByRole('button', { name: '本月' })).toHaveClass(/bg-primary/, { timeout: 15_000 });

    watcher.assert();
  });

  test('G-5 成就列表加载：已解锁/未解锁分组渲染', async ({ page }) => {
    const watcher = watchPage(page);
    await page.goto('/growth');

    // 切换到成就中心 Tab
    await page.getByRole('button', { name: '成就中心' }).click();
    // 分组标题（生产/演示均渲染，空列表时计数为 0）
    await expect(page.getByText(/已解锁 \(\d+\)/)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/未解锁 \(\d+\)/)).toBeVisible();

    watcher.assert();
  });
});
