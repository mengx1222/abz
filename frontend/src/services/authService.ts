import api from './api';
import { LoginRequest, TokenData, UserInfo } from '../types/auth';

export interface BackendResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  request_id?: string;
}

export async function loginWithCode(data: LoginRequest): Promise<TokenData> {
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
