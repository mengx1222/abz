import { useAuthStore } from '../stores/authStore';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

export function useAuth() {
  const { user, token, isAuthenticated, isLoading, login, logout, setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = useCallback(
    async (phone: string, code: string) => {
      await login(phone, code);
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
