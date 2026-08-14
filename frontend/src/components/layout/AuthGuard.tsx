import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import type { ReactNode } from 'react';

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const token = useAuthStore((s) => s.token);
  const location = useLocation();

  // Show loading while checking auth state
  if (!token && !isAuthenticated) {
    // Not authenticated, redirect to login
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  // If we have token but no user yet, we could load user here
  // For now, just render children
  return <>{children}</>;
}
