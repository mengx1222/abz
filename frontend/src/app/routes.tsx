import React, { Suspense, ComponentType } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { AuthGuard } from '../components/layout/AuthGuard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

/**
 * 辅助函数：从命名导出的模块创建懒加载组件
 * 用法: lazyNamed(() => import('./Foo'), 'FooPage')
 */
function lazyNamed<T extends string>(
  factory: () => Promise<Record<T, ComponentType>>,
  name: T
): ComponentType {
  // React 19 lazy 泛型需显式指定：module[name] 是 ComponentType 联合，推断会退化为 {} 触发 TS2322
  const LazyComp = React.lazy<ComponentType>(() =>
    factory().then((module) => ({ default: module[name] }))
  );
  return function LazyPage() {
    return (
      <Suspense fallback={<LoadingSpinner />}>
        <LazyComp />
      </Suspense>
    );
  };
}

// Lazy load pages (named exports)
const DashboardPage = lazyNamed(
  () => import('../features/dashboard/DashboardPage'),
  'DashboardPage'
);
const ProductQaPage = lazyNamed(
  () => import('../features/product-qa/ProductQaPage'),
  'ProductQaPage'
);
const CustomersPage = lazyNamed(
  () => import('../features/customers/CustomersPage'),
  'CustomersPage'
);
const CustomerDetailPage = lazyNamed(
  () => import('../features/customers/CustomerDetailPage'),
  'CustomerDetailPage'
);
const ScriptsPage = lazyNamed(
  () => import('../features/scripts/ScriptsPage'),
  'ScriptsPage'
);
const TrainingPage = lazyNamed(
  () => import('../features/training/TrainingPage'),
  'TrainingPage'
);
const TrainingChatPage = lazyNamed(
  () => import('../features/training/TrainingChatPage'),
  'TrainingChatPage'
);
const CommunityPage = lazyNamed(
  () => import('../features/community/CommunityPage'),
  'CommunityPage'
);
const GrowthPage = lazyNamed(
  () => import('../features/growth/GrowthPage'),
  'GrowthPage'
);
const NotificationsPage = lazyNamed(
  () => import('../features/notifications/NotificationsPage'),
  'NotificationsPage'
);
const KnowledgePage = lazyNamed(
  () => import('../features/knowledge/KnowledgePage'),
  'KnowledgePage'
);
const UsersPage = lazyNamed(
  () => import('../features/admin/UsersPage'),
  'UsersPage'
);
const AnalyticsPage = lazyNamed(
  () => import('../features/admin/AnalyticsPage'),
  'AnalyticsPage'
);
const AuditLogPage = lazyNamed(
  () => import('../features/admin/AuditLogPage'),
  'AuditLogPage'
);
const CompliancePage = lazyNamed(
  () => import('../features/admin/CompliancePage'),
  'CompliancePage'
);
const CommunityManagePage = lazyNamed(
  () => import('../features/admin/CommunityManagePage'),
  'CommunityManagePage'
);
const ScriptManagePage = lazyNamed(
  () => import('../features/admin/ScriptManagePage'),
  'ScriptManagePage'
);
const TrainingManagePage = lazyNamed(
  () => import('../features/admin/TrainingManagePage'),
  'TrainingManagePage'
);
const SettingsPage = lazyNamed(
  () => import('../features/admin/SettingsPage'),
  'SettingsPage'
);

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
    lazy: () =>
      import('../features/auth/LoginPage').then((m) => ({
        Component: m.LoginPage,
      })),
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
