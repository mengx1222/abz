/**
 * 角色路由配置 — 定义每个页面允许访问的角色
 */

/** 所有角色常量，方便引用 */
const ALL_ROLES = [
  "SYSTEM_ADMIN",
  "HQ_ADMIN",
  "BRANCH_ADMIN",
  "TEAM_LEADER",
  "COMPLIANCE",
  "KNOWLEDGE_ADMIN",
  "AGENT",
] as const;

/** 管理员角色 */
const ADMIN_ROLES = ["SYSTEM_ADMIN", "HQ_ADMIN"] as const;

/** 路径 → 允许的角色列表 */
export const ROLE_ACCESS: Record<string, readonly string[]> = {
  // 业务页面（所有角色可访问）
  "/dashboard": ALL_ROLES,
  "/product-qa": ALL_ROLES,
  "/customers": ALL_ROLES,
  "/scripts": ALL_ROLES,
  "/training": ALL_ROLES,
  "/community": ALL_ROLES,
  "/growth": ALL_ROLES,
  "/notifications": ALL_ROLES,
  "/knowledge": ["SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN", "KNOWLEDGE_ADMIN", "AGENT"],

  // 管理页面（仅管理员）
  "/admin/users": ADMIN_ROLES,
  "/admin/analytics": ADMIN_ROLES,
  "/admin/audit-logs": ADMIN_ROLES,
  "/admin/audit": ADMIN_ROLES,
  "/admin/compliance": ["SYSTEM_ADMIN", "HQ_ADMIN", "COMPLIANCE"],
  "/admin/community": ADMIN_ROLES,
  "/admin/scripts": ADMIN_ROLES,
  "/admin/training": ADMIN_ROLES,
  "/admin/settings": ["SYSTEM_ADMIN"],
};

/**
 * 判断用户是否有权访问某路径
 * - 先精确匹配
 * - 再前缀匹配（最长前缀优先）
 * - 默认允许
 */
export function hasRouteAccess(path: string, roleCode: string): boolean {
  // 精确匹配
  if (ROLE_ACCESS[path]) {
    return ROLE_ACCESS[path].includes(roleCode);
  }
  // 前缀匹配（如 /admin 匹配 /admin/*），最长前缀优先
  const matchingKey = Object.keys(ROLE_ACCESS)
    .filter((k) => path.startsWith(k + "/") || path === k)
    .sort((a, b) => b.length - a.length)[0];
  if (matchingKey) {
    return ROLE_ACCESS[matchingKey].includes(roleCode);
  }
  // 默认允许
  return true;
}
