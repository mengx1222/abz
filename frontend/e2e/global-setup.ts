import { request } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

/**
 * E2E Global Setup（Task 11）
 *
 * 1. 用确定性 AGENT 账号登录后端（13800138000 / 888888），保存 storageState
 *    （login-flow 项目除外 —— 它测真实表单登录，不读 storageState）
 * 2. 幂等创建确定性测试客户（E2E-张先生 / 13900001111），供客户列表/详情 E2E 使用
 *
 * 数据确定性：手机号、姓名固定；不存在则创建，存在则复用 —— 每次运行结果可预测。
 */
const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000/api/v1';
const PHONE = '13800138000';
const CODE = '888888';
const CUSTOMER_NAME = 'E2E-张先生';
const CUSTOMER_PHONE = '13900001111';
const AUTH_FILE = path.join(__dirname, '.auth', 'user.json');

async function login(api: any): Promise<string> {
  const res = await api.post(`${API_BASE}/auth/login`, {
    data: { phone: PHONE, verification_code: CODE },
  });
  if (res.status() !== 200) {
    throw new Error(`E2E login failed: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  return body.data.access_token;
}

async function ensureCustomer(api: any, token: string): Promise<void> {
  const headers = { Authorization: `Bearer ${token}` };
  // 1) 尝试按手机号查找（确定性：固定手机号）
  const list = await api.get(`${API_BASE}/customers?search=${CUSTOMER_PHONE}&page=1&page_size=10`, {
    headers,
  });
  const listBody = await list.json();
  const items = listBody.data || [];
  const existing = items.find(
    (c: any) => c.phone === CUSTOMER_PHONE && c.name === CUSTOMER_NAME,
  );
  if (existing) {
    console.log(`[setup] customer exists: ${existing.id}`);
    return;
  }
  // 2) 不存在则创建
  const created = await api.post(`${API_BASE}/customers`, {
    headers,
    data: {
      name: CUSTOMER_NAME,
      phone: CUSTOMER_PHONE,
      customer_type: 'personal',
      current_stage: 'needs_analysis',
      intention_level: 3,
      age: 42,
      gender: 'male',
      occupation: '企业职员',
      note: 'Playwright E2E 确定性测试客户（幂等创建）',
    },
  });
  if (created.status() !== 200 && created.status() !== 201) {
    // 创建可能因重复手机号失败（幂等）：若 409/400 说明已存在，忽略
    console.log(`[setup] customer create status=${created.status()}, body=${await created.text()}`);
  } else {
    console.log('[setup] customer created');
  }
}

export default async function globalSetup(): Promise<void> {
  const api = await request.newContext({ baseURL: API_BASE });

  const token = await login(api);
  console.log('[setup] login ok');

  // 保存 storageState（storage 里存 token 供前端 authStore 读取）
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  fs.writeFileSync(
    AUTH_FILE,
    JSON.stringify({
      cookies: [],
      origins: [
        {
          origin: process.env.E2E_FRONTEND_ORIGIN || 'http://localhost:3000',
          localStorage: [
            { name: 'azb_token', value: token },
            { name: 'azb_user', value: JSON.stringify({ phone: PHONE, name: '林思远' }) },
          ],
        },
      ],
    }),
  );
  console.log('[setup] storageState saved');

  await ensureCustomer(api, token);
  console.log('[setup] customer ready');

  await api.dispose();
}
