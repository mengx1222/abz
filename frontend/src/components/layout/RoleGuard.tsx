/**
 * 角色路由守卫 — 检查用户是否有权访问当前页面
 */
import { useLocation, Navigate } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";
import { hasRouteAccess } from "../../config/roleRoutes";

export function RoleGuard({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!hasRouteAccess(location.pathname, user.role_code || "AGENT")) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <h2 className="text-xl font-semibold text-gray-700">权限不足</h2>
        <p className="text-gray-500 mt-2">您没有权限访问此页面</p>
        <a
          href="/"
          className="mt-4 text-blue-600 hover:underline"
        >
          返回首页
        </a>
      </div>
    );
  }

  return <>{children}</>;
}
