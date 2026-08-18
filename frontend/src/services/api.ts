import axios from 'axios';
import { useAuthStore } from '../stores/authStore';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: handle errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Task 24 (P2-2): auth 端点自身的 401（登录失败/刷新失败）交由调用方处理，
      // 不得触发登出跳转 —— 否则登录失败会导致整页刷新、错误提示被冲掉。
      // 非 auth 端点的 401 = 会话过期 → 清理凭据并跳转登录页。
      const requestUrl: unknown = error.config?.url;
      const isAuthEndpoint =
        typeof requestUrl === 'string' && requestUrl.startsWith('/auth/');
      if (!isAuthEndpoint) {
        const store = useAuthStore.getState();
        store.logout();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
