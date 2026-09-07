import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '../../stores/authStore';

// Mock authService
vi.mock('../../services/authService', () => ({
  loginWithCredentials: vi.fn(),
  getCurrentUser: vi.fn(),
}));

import { loginWithCredentials, getCurrentUser } from '../../services/authService';
const mockedLogin = vi.mocked(loginWithCredentials);
const mockedGetCurrentUser = vi.mocked(getCurrentUser);

const mockUser = {
  id: '1',
  phone: '13800138000',
  name: 'Test User',
  role_code: 'AGENT',
  role_name: '代理人',
  organization_id: 'org1',
  status: 'active',
  demo_mode: false,
  created_at: '2024-01-01T00:00:00Z',
};

describe('authStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Reset store state
    const store = useAuthStore.getState();
    store.logout();
  });

  it('initial state is unauthenticated when no token in localStorage', () => {
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isLoading).toBe(false);
  });

  it('login sets user and token', async () => {
    mockedLogin.mockResolvedValue({
      access_token: 'test-access-token',
      refresh_token: 'test-refresh-token',
      token_type: 'Bearer',
      expires_in: 3600,
    });
    mockedGetCurrentUser.mockResolvedValue(mockUser);

    const store = useAuthStore.getState();
    await store.login({ phone: '13800138000', verification_code: '123456' });

    const state = useAuthStore.getState();
    expect(state.token).toBe('test-access-token');
    expect(state.user).toEqual(mockUser);
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
  });

  it('login with password passes password through to service (production mode)', async () => {
    mockedLogin.mockResolvedValue({
      access_token: 'pwd-token',
      refresh_token: 'refresh',
      token_type: 'Bearer',
      expires_in: 3600,
    });
    mockedGetCurrentUser.mockResolvedValue(mockUser);

    await useAuthStore.getState().login({ phone: '13900139000', password: 'Secret#2026' });

    expect(mockedLogin).toHaveBeenCalledWith({ phone: '13900139000', password: 'Secret#2026' });
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('logout clears state', async () => {
    // First login
    mockedLogin.mockResolvedValue({
      access_token: 'token',
      refresh_token: 'refresh',
      token_type: 'Bearer',
      expires_in: 3600,
    });
    mockedGetCurrentUser.mockResolvedValue(mockUser);

    await useAuthStore.getState().login({ phone: '13800138000', verification_code: '123456' });

    // Then logout
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(localStorage.getItem('abz_token')).toBeNull();
    expect(localStorage.getItem('abz_user')).toBeNull();
  });

  it('isAuthenticated reflects login state', async () => {
    expect(useAuthStore.getState().isAuthenticated).toBe(false);

    mockedLogin.mockResolvedValue({
      access_token: 'token',
      refresh_token: 'refresh',
      token_type: 'Bearer',
      expires_in: 3600,
    });
    mockedGetCurrentUser.mockResolvedValue(mockUser);

    await useAuthStore.getState().login({ phone: '13800138000', verification_code: '123456' });
    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    useAuthStore.getState().logout();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('login persists token to localStorage', async () => {
    mockedLogin.mockResolvedValue({
      access_token: 'persisted-token',
      refresh_token: 'refresh',
      token_type: 'Bearer',
      expires_in: 3600,
    });
    mockedGetCurrentUser.mockResolvedValue(mockUser);

    await useAuthStore.getState().login({ phone: '13800138000', verification_code: '123456' });

    expect(localStorage.getItem('abz_token')).toBe('persisted-token');
    expect(JSON.parse(localStorage.getItem('abz_user')!)).toEqual(mockUser);
  });

  it('login throws on failure and clears isLoading', async () => {
    mockedLogin.mockRejectedValue(new Error('Network error'));

    await expect(
      useAuthStore.getState().login({ phone: '13800138000', password: 'wrong' })
    ).rejects.toThrow('登录失败，请检查手机号和验证码');

    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  it('setUser updates user state', () => {
    useAuthStore.getState().setUser(mockUser);
    expect(useAuthStore.getState().user).toEqual(mockUser);
    expect(JSON.parse(localStorage.getItem('abz_user')!)).toEqual(mockUser);
  });
});
