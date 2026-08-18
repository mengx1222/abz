import { create } from 'zustand';
import { UserInfo } from '../types/auth';
import { loginWithCode, getCurrentUser } from '../services/authService';
import { getApiErrorMessage } from '../utils/apiError';

interface AuthState {
  user: UserInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (phone: string, code: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  setUser: (user: UserInfo) => void;
}

const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem('abz_token');
  } catch {
    return null;
  }
};

const getStoredUser = (): UserInfo | null => {
  try {
    const raw = localStorage.getItem('abz_user');
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

export const useAuthStore = create<AuthState>((set) => ({
  user: getStoredUser(),
  token: getStoredToken(),
  isAuthenticated: !!getStoredToken(),
  isLoading: false,

  login: async (phone: string, code: string) => {
    set({ isLoading: true });
    try {
      const tokenData = await loginWithCode({ phone, verification_code: code });

      localStorage.setItem('abz_token', tokenData.access_token);

      set({ token: tokenData.access_token, isLoading: false });

      // Fetch user info with the new token
      try {
        const user = await getCurrentUser();
        localStorage.setItem('abz_user', JSON.stringify(user));
        set({ user, isAuthenticated: true });
      } catch {
        // If fetching user fails, still consider logged in with token
        set({ isAuthenticated: true });
      }
    } catch (err) {
      // Task 24 (P2-2): 透传后端真实错误消息（如「手机号或密码错误」），
      // 不再吞成固定文案；后端未提供消息时保留通用提示。
      set({ isLoading: false });
      throw new Error(getApiErrorMessage(err, '登录失败，请检查手机号和验证码'));
    }
  },

  logout: () => {
    localStorage.removeItem('abz_token');
    localStorage.removeItem('abz_user');
    set({ user: null, token: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    const token = getStoredToken();
    if (!token) return;
    try {
      const user = await getCurrentUser();
      localStorage.setItem('abz_user', JSON.stringify(user));
      set({ user, isAuthenticated: true });
    } catch {
      // Token might be expired
      set({ user: null, token: null, isAuthenticated: false });
      localStorage.removeItem('abz_token');
      localStorage.removeItem('abz_user');
    }
  },

  setUser: (user: UserInfo) => {
    localStorage.setItem('abz_user', JSON.stringify(user));
    set({ user });
  },
}));
