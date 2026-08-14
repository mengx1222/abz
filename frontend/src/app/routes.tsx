import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { AuthGuard } from '../components/layout/AuthGuard';
import { LoginPage } from '../features/auth/LoginPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { ProductQaPage } from '../features/product-qa/ProductQaPage';
import { CustomersPage } from '../features/customers/CustomersPage';
import { ScriptsPage } from '../features/scripts/ScriptsPage';
import { TrainingPage } from '../features/training/TrainingPage';
import { CommunityPage } from '../features/community/CommunityPage';
import { GrowthPage } from '../features/growth/GrowthPage';
import { NotificationsPage } from '../features/notifications/NotificationsPage';

function ProtectedLayout() {
  return (
    <AuthGuard>
      <AppLayout />
    </AuthGuard>
  );
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <ProtectedLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'product-qa', element: <ProductQaPage /> },
      { path: 'customers', element: <CustomersPage /> },
      { path: 'scripts', element: <ScriptsPage /> },
      { path: 'training', element: <TrainingPage /> },
      { path: 'community', element: <CommunityPage /> },
      { path: 'growth', element: <GrowthPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
    ],
  },
]);
