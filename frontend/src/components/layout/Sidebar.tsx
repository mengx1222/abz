import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../utils/cn';
import { useAuthStore } from '../../stores/authStore';
import { Avatar } from '../ui/Avatar';

interface NavItem {
  label: string;
  path: string;
  icon: string;
}

interface NavGroup {
  label?: string;
  items: NavItem[];
}

const mainNav: NavGroup = {
  items: [
    { label: '工作台', path: '/dashboard', icon: '🏠' },
    { label: 'AI产品专家', path: '/product-qa', icon: '🤖' },
    { label: '客户360', path: '/customers', icon: '👥' },
    { label: 'AI话术', path: '/scripts', icon: '💬' },
    { label: 'AI陪练', path: '/training', icon: '🎯' },
    { label: 'AI社区', path: '/community', icon: '🌐' },
    { label: '我的成长', path: '/growth', icon: '📊' },
    { label: '消息中心', path: '/notifications', icon: '🔔' },
  ],
};

const adminNav: NavGroup = {
  label: '管理后台',
  items: [
    { label: '团队管理', path: '/admin/team', icon: '📋' },
    { label: '知识库管理', path: '/knowledge', icon: '📚' },
    { label: '数据报表', path: '/admin/reports', icon: '📈' },
  ],
};

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const [adminExpanded, setAdminExpanded] = useState(false);

  const isAdmin = user && user.role_code !== 'AGENT';

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
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-sm">安</span>
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-white text-sm font-semibold leading-tight truncate">
                安诊保 AI 副驾
              </h1>
              <p className="text-sidebar-text text-[10px] leading-tight mt-0.5">
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
          className="w-full flex items-center justify-center h-7 rounded-md text-sidebar-text hover:text-sidebar-text-active hover:bg-sidebar-hover transition-colors cursor-pointer text-xs"
        >
          {collapsed ? '→' : '← 收起'}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-1">
        <div className="flex flex-col gap-0.5">
          {mainNav.items.map((item) => (
            <SidebarNavLink key={item.path} item={item} collapsed={collapsed} active={location.pathname === item.path} />
          ))}
        </div>

        {/* Admin section */}
        {isAdmin && (
          <div className="mt-4">
            {!collapsed && (
              <button
                onClick={() => setAdminExpanded(!adminExpanded)}
                className="flex items-center gap-1.5 w-full px-2 py-1.5 text-[11px] font-medium text-sidebar-text/50 uppercase tracking-wider hover:text-sidebar-text transition-colors cursor-pointer"
              >
                <span className={cn('transition-transform', adminExpanded && 'rotate-90')}>▶</span>
                {adminNav.label}
              </button>
            )}
            {(adminExpanded || collapsed) && (
              <div className="flex flex-col gap-0.5 mt-0.5">
                {adminNav.items.map((item) => (
                  <SidebarNavLink key={item.path} item={item} collapsed={collapsed} active={location.pathname === item.path} />
                ))}
              </div>
            )}
          </div>
        )}
      </nav>

      {/* User section at bottom */}
      <div className="flex-shrink-0 border-t border-white/10 px-3 py-3">
        <div className={cn('flex items-center gap-3', collapsed && 'justify-center')}>
          <Avatar name={user?.name || '用户'} size="sm" className="!h-8 !w-8" />
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
  return (
    <NavLink
      to={item.path}
      title={collapsed ? item.label : undefined}
      className={cn(
        'flex items-center gap-2.5 h-9 px-2.5 rounded-lg text-sm transition-colors duration-150 group',
        active
          ? 'bg-sidebar-active text-sidebar-text-active'
          : 'text-sidebar-text hover:text-sidebar-text-active hover:bg-sidebar-hover'
      )}
    >
      <span className="text-base flex-shrink-0 w-5 text-center">{item.icon}</span>
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  );
}
