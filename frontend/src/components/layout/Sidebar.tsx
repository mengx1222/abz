import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  Users,
  Rocket,
  MessageSquareText,
  Target,
  Globe,
  TrendingUp,
  Bell,
  UserCog,
  BarChart3,
  ScrollText,
  ShieldCheck,
  MessagesSquare,
  MessageSquareQuote,
  GraduationCap,
  Library,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronRight,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { useAuthStore } from '../../stores/authStore';
import { Avatar } from '../ui/Avatar';

type RoleList = string[] | "all";

interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  roles?: RoleList;
}

interface NavGroup {
  label?: string;
  items: NavItem[];
}

const mainNav: NavGroup = {
  items: [
    { label: '工作台', path: '/dashboard', icon: LayoutDashboard, roles: 'all' },
    { label: 'AI产品专家', path: '/product-qa', icon: Bot, roles: 'all' },
    { label: '客户360', path: '/customers', icon: Users, roles: 'all' },
    { label: 'AI销售副驾', path: '/sales-agent', icon: Rocket, roles: 'all' },
    { label: 'AI话术', path: '/scripts', icon: MessageSquareText, roles: 'all' },
    { label: 'AI陪练', path: '/training', icon: Target, roles: 'all' },
    { label: 'AI社区', path: '/community', icon: Globe, roles: 'all' },
    { label: '我的成长', path: '/growth', icon: TrendingUp, roles: 'all' },
    { label: '消息中心', path: '/notifications', icon: Bell, roles: 'all' },
  ],
};

const adminNav: NavGroup = {
  label: '管理后台',
  items: [
    { label: '用户管理', path: '/admin/users', icon: UserCog, roles: ['SYSTEM_ADMIN', 'HQ_ADMIN'] },
    { label: '数据看板', path: '/admin/analytics', icon: BarChart3, roles: ['SYSTEM_ADMIN', 'HQ_ADMIN'] },
    { label: '审计日志', path: '/admin/audit', icon: ScrollText, roles: ['SYSTEM_ADMIN', 'HQ_ADMIN'] },
    { label: '合规中心', path: '/admin/compliance', icon: ShieldCheck, roles: ['SYSTEM_ADMIN', 'HQ_ADMIN', 'COMPLIANCE'] },
    { label: '社区管理', path: '/admin/community', icon: MessagesSquare, roles: ['SYSTEM_ADMIN', 'HQ_ADMIN'] },
    { label: '话术管理', path: '/admin/scripts', icon: MessageSquareQuote, roles: ['SYSTEM_ADMIN', 'HQ_ADMIN'] },
    { label: '陪练场景', path: '/admin/training', icon: GraduationCap, roles: ['SYSTEM_ADMIN', 'HQ_ADMIN'] },
    { label: '知识库', path: '/knowledge', icon: Library, roles: ['SYSTEM_ADMIN', 'HQ_ADMIN', 'BRANCH_ADMIN', 'KNOWLEDGE_ADMIN', 'AGENT'] },
    { label: '系统设置', path: '/admin/settings', icon: Settings, roles: ['SYSTEM_ADMIN'] },
  ],
};

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const [adminExpanded, setAdminExpanded] = useState(false);

  const userRoleCode = user?.role_code || 'AGENT';

  /** 按角色过滤导航项 */
  const filterByRole = (item: NavItem) => {
    if (!item.roles || item.roles === 'all') return true;
    return (item.roles as string[]).includes(userRoleCode);
  };

  const filteredMainItems = mainNav.items.filter(filterByRole);
  const filteredAdminItems = adminNav.items.filter(filterByRole);
  const isAdmin = filteredAdminItems.length > 0;

  return (
    <aside
      className={cn(
        'h-full bg-sidebar flex flex-col transition-all duration-200 ease-in-out flex-shrink-0',
        collapsed ? 'w-[68px]' : 'w-[240px]'
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 flex-shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center flex-shrink-0 shadow-xs">
            <span className="text-white font-bold text-sm">安</span>
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-white text-sm font-semibold leading-tight truncate">
                安诊保 AI 副驾
              </h1>
              <p className="text-sidebar-text/70 text-[10px] leading-tight mt-0.5">
                Intelligent Insurance Co-pilot
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <div className="px-3 mb-1 flex-shrink-0">
        <button
          onClick={onToggle}
          aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
          className="w-full flex items-center justify-center h-7 rounded-md text-sidebar-text hover:text-sidebar-text-active hover:bg-sidebar-hover transition-colors cursor-pointer"
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <>
              <PanelLeftClose className="h-4 w-4" />
              <span className="ml-1.5 text-xs">收起</span>
            </>
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-1">
        <div className="flex flex-col gap-0.5">
          {filteredMainItems.map((item) => (
            <SidebarNavLink key={item.path} item={item} collapsed={collapsed} active={location.pathname === item.path || location.pathname.startsWith(item.path + '/')} />
          ))}
        </div>

        {/* Admin section */}
        {isAdmin && (
          <div className="mt-4">
            {!collapsed && (
              <button
                onClick={() => setAdminExpanded(!adminExpanded)}
                aria-expanded={adminExpanded}
                className="flex items-center gap-1 w-full px-2 py-1.5 text-[11px] font-medium text-sidebar-text/50 uppercase tracking-wider hover:text-sidebar-text transition-colors cursor-pointer"
              >
                <ChevronRight className={cn('h-3 w-3 transition-transform', adminExpanded && 'rotate-90')} />
                {adminNav.label}
              </button>
            )}
            {(adminExpanded || collapsed) && (
              <div className="flex flex-col gap-0.5 mt-0.5">
                {filteredAdminItems.map((item) => (
                  <SidebarNavLink key={item.path} item={item} collapsed={collapsed} active={location.pathname === item.path || location.pathname.startsWith(item.path + '/')} />
                ))}
              </div>
            )}
          </div>
        )}
      </nav>

      {/* User section at bottom */}
      <div className="flex-shrink-0 border-t border-white/10 px-3 py-3">
        <div className={cn('flex items-center gap-3', collapsed && 'justify-center')}>
          <Avatar name={user?.name || '用户'} size="sm" className="h-8 w-8" />
          {!collapsed && user && (
            <div className="min-w-0">
              <p className="text-white text-sm font-medium truncate">{user.name}</p>
              <p className="text-sidebar-text text-[11px] truncate">{user.role_name || '未分配角色'}</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function SidebarNavLink({
  item,
  collapsed,
  active,
}: {
  item: NavItem;
  collapsed: boolean;
  active: boolean;
}) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.path}
      title={collapsed ? item.label : undefined}
      className={cn(
        'relative flex items-center gap-2.5 h-9 px-2.5 rounded-lg text-sm transition-colors duration-150 group',
        active
          ? 'bg-sidebar-active text-sidebar-text-active font-medium'
          : 'text-sidebar-text hover:text-sidebar-text-active hover:bg-sidebar-hover'
      )}
    >
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-accent" aria-hidden="true" />
      )}
      <Icon className="h-[18px] w-[18px] flex-shrink-0" strokeWidth={active ? 2 : 1.8} />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  );
}
