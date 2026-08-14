import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { AuthGuard } from '../components/layout/AuthGuard';
import { LoginPage } from '../features/auth/LoginPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { ProductQaPage } from '../features/product-qa/ProductQaPage';
import { CustomersPage } from '../features/customers/CustomersPage';
import { CustomerDetailPage } from '../features/customers/CustomerDetailPage';
import { ScriptsPage } from '../features/scripts/ScriptsPage';
import { TrainingPage } from '../features/training/TrainingPage';
import { TrainingChatPage } from '../features/training/TrainingChatPage';
import { CommunityPage } from '../features/community/CommunityPage';
import { GrowthPage } from '../features/growth/GrowthPage';
import { NotificationsPage } from '../features/notifications/NotificationsPage';
import { KnowledgePage } from '../features/knowledge/KnowledgePage';
import { UsersPage } from '../features/admin/UsersPage';
import { AnalyticsPage } from '../features/admin/AnalyticsPage';
import { AuditLogPage } from '../features/admin/AuditLogPage';
import { CompliancePage } from '../features/admin/CompliancePage';
import { CommunityManagePage } from '../features/admin/CommunityManagePage';
import { ScriptManagePage } from '../features/admin/ScriptManagePage';
import { TrainingManagePage } from '../features/admin/TrainingManagePage';
import { SettingsPage } from '../features/admin/SettingsPage';

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
      { path: 'customers/:id', element: <CustomerDetailPage /> },
      { path: 'scripts', element: <ScriptsPage /> },
      { path: 'training', element: <TrainingPage /> },
      { path: 'training/chat/:scenarioId', element: <TrainingChatPage /> },
      { path: 'community', element: <CommunityPage /> },
      { path: 'growth', element: <GrowthPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
      { path: 'knowledge', element: <KnowledgePage /> },
      // 管理后台
      { path: 'admin/users', element: <UsersPage /> },
      { path: 'admin/analytics', element: <AnalyticsPage /> },
      { path: 'admin/audit', element: <AuditLogPage /> },
      { path: 'admin/compliance', element: <CompliancePage /> },
      { path: 'admin/community', element: <CommunityManagePage /> },
      { path: 'admin/scripts', element: <ScriptManagePage /> },
      { path: 'admin/training', element: <TrainingManagePage /> },
      { path: 'admin/settings', element: <SettingsPage /> },
    ],
  },
]);
