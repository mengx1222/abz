import { useAuthStore } from '../stores/authStore';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import type { LoginRequest } from '../types/auth';

export function useAuth() {
  const { user, token, isAuthenticated, isLoading, login, logout, setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = useCallback(
    async (credentials: LoginRequest) => {
      await login(credentials);
      navigate('/dashboard');
    },
    [login, navigate]
  );

  const handleLogout = useCallback(() => {
    logout();
    navigate('/login');
  }, [logout, navigate]);

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login: handleLogin,
    logout: handleLogout,
    setUser,
  };
}
