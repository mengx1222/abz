import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
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

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

/** 单飞刷新：并发 401 只触发一次 /auth/refresh，其余请求复用同一 promise。 */
let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const store = useAuthStore.getState();
    const refreshToken = store.refreshToken;
    if (!refreshToken) return false;
    try {
      // 用裸 axios 调刷新，避免进入本实例拦截器造成递归
      const resp = await axios.post(
        '/api/v1/auth/refresh',
        { refresh_token: refreshToken },
        { timeout: 15000 }
      );
      const data = resp.data?.data;
      if (data?.access_token) {
        useAuthStore
          .getState()
          .applyRefreshedTokens(data.access_token, data.refresh_token ?? refreshToken);
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

// Response interceptor: 401 时自动刷新重试（会话续期），失败才登出
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Task 24 (P2-2): auth 端点自身的 401（登录失败/刷新失败）交由调用方处理，
      // 不得触发登出跳转 —— 否则登录失败会导致整页刷新、错误提示被冲掉。
      const requestUrl = error.config?.url;
      const isAuthEndpoint =
        typeof requestUrl === 'string' && requestUrl.startsWith('/auth/');
      const config = error.config as RetriableConfig | undefined;
      if (!isAuthEndpoint && config && !config._retried) {
        config._retried = true;
        return tryRefreshToken().then((ok) => {
          if (ok) {
            const { token } = useAuthStore.getState();
            return api.request({
              ...config,
              headers: { ...config.headers, Authorization: `Bearer ${token}` },
            });
          }
          const store = useAuthStore.getState();
          store.logout();
          window.location.href = '/login';
          return Promise.reject(error);
        });
      }
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