import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E 配置（Task 11 — 核心黄金路径第一阶段）
 *
 * 运行前提（CI workflow 负责）：
 *   - backend 已启动（DEMO_MODE=false + mock AI provider），端口 8000
 *   - PostgreSQL + Redis 已就绪，alembic + seed 已执行
 *   - frontend dev server（vite, :3000, 代理 /api → :8000）
 *
 * 测试用户：AGENT 13800138000 / 888888（seed 固定账号）
 * 确定性客户：由 global-setup 通过 API 幂等创建（E2E-张先生）
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  workers: 1, // 串行：共享同一个后端/DB，避免确定性数据相互干扰
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['html', { open: 'never' }], ['list']]
    : [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // 捕获浏览器控制台错误：console error / pageerror 视为测试失败
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth/user.json',
      },
      // 登录测试单独项目：真实表单登录，不依赖预置 session
      testIgnore: /auth\/login\.spec\.ts/,
    },
    {
      name: 'login-flow',
      testMatch: /auth\/login\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        // 登录测试从空白 session 开始
        storageState: { cookies: [], origins: [] },
      },
    },
  ],
  globalSetup: './e2e/global-setup.ts',
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: {
      VITE_API_PROXY: process.env.E2E_API_TARGET || 'http://localhost:8000',
    },
  },
});
