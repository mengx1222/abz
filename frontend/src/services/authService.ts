import api from './api';
import { LoginRequest, TokenData, UserInfo } from '../types/auth';

export interface BackendResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  request_id?: string;
}

/** 登录：demo 用 verification_code，生产用 password（后端按字段择一验证）。 */
export async function loginWithCredentials(data: LoginRequest): Promise<TokenData> {
  const response = await api.post<BackendResponse<TokenData>>('/auth/login', data);
  return response.data.data;
}

export async function getCurrentUser(): Promise<UserInfo> {
  const response = await api.get<BackendResponse<UserInfo>>('/auth/me');
  return response.data.data;
}

export async function refreshToken(refreshTokenValue: string): Promise<TokenData> {
  const response = await api.post<BackendResponse<TokenData>>('/auth/refresh', {
    refresh_token: refreshTokenValue,
  });
  return response.data.data;
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<string> {
  const response = await api.post<BackendResponse<{ message: string }>>('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  });
  return response.data.data.message;
}

/**
 * 探测运行模式（登录页按模式切换表单）。
 * demo 模式：手机号 + 统一验证码 + 快捷登录面板；生产：手机号 + 密码。
 * 探测失败按生产处理（更保守：密码表单），避免把错误账号暴露给真实用户。
 */
export async function fetchAuthMode(): Promise<'demo' | 'password'> {
  try {
    const response = await api.get<BackendResponse<{ demo_mode: boolean }>>('/health');
    return response.data.data.demo_mode ? 'demo' : 'password';
  } catch {
    return 'password';
  }
}
