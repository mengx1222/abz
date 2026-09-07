import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Bell, ChevronDown, Sparkles, LogOut, Settings, KeyRound } from 'lucide-react';
import { cn } from '../../utils/cn';
import { Avatar } from '../ui/Avatar';
import { useAuthStore } from '../../stores/authStore';
import { useAssistantStore } from '../../stores/assistantStore';
import { ChangePasswordModal } from '../../features/settings/ChangePasswordModal';

export function TopBar() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const toggleAssistant = useAssistantStore((s) => s.toggle);
  const [searchValue, setSearchValue] = useState('');
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6 flex-shrink-0">
      {/* Left: Search */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search
            aria-hidden="true"
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted"
          />
          <input
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="搜索产品、客户、话术..."
            className="w-full h-9 pl-9 pr-4 rounded-lg border border-border bg-bg text-sm text-text placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent focus:bg-card transition-colors"
          />
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2 ml-4">
        {/* AI Assistant Button */}
        <button
          onClick={toggleAssistant}
          aria-haspopup="dialog"
          title="全局 AI 助手"
          className="h-9 px-3.5 rounded-lg bg-accent/10 text-accent text-sm font-medium hover:bg-accent/20 transition-colors flex items-center gap-1.5 cursor-pointer"
        >
          <Sparkles className="h-4 w-4" />
          <span>AI 助手</span>
        </button>

        {/* Notification Bell */}
        <button
          onClick={() => navigate('/notifications')}
          aria-label="消息通知"
          className="relative h-9 w-9 flex items-center justify-center rounded-lg text-muted hover:text-text hover:bg-bg transition-colors cursor-pointer"
        >
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.8} />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-error rounded-full ring-2 ring-card" />
        </button>

        {/* User Menu */}
        <div ref={userMenuRef} className="relative">
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            aria-haspopup="menu"
            aria-expanded={userMenuOpen}
            className={cn(
              'flex items-center gap-2 h-9 pl-1 pr-2 rounded-lg transition-colors cursor-pointer',
              userMenuOpen ? 'bg-bg' : 'hover:bg-bg'
            )}
          >
            <Avatar name={user?.name || '用户'} size="sm" className="h-7 w-7" />
            <span className="text-sm text-text max-w-[80px] truncate hidden sm:inline">{user?.name}</span>
            <ChevronDown
              className={cn('h-3.5 w-3.5 text-muted transition-transform', userMenuOpen && 'rotate-180')}
            />
          </button>

          {userMenuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full mt-1 w-48 bg-card rounded-lg border border-border shadow-pop py-1 animate-scale-in origin-top-right z-50"
            >
              <div className="px-3 py-2 border-b border-border">
                <p className="text-sm font-medium text-text">{user?.name}</p>
                <p className="text-xs text-muted">{user?.phone}</p>
              </div>
              <button
                onClick={() => { setUserMenuOpen(false); setChangePasswordOpen(true); }}
                role="menuitem"
                className="w-full text-left px-3 py-2 text-sm text-text hover:bg-bg transition-colors cursor-pointer flex items-center gap-2"
              >
                <KeyRound className="h-4 w-4 text-muted" />
                修改密码
              </button>
              <button
                onClick={() => { setUserMenuOpen(false); }}
                role="menuitem"
                className="w-full text-left px-3 py-2 text-sm text-text hover:bg-bg transition-colors cursor-pointer flex items-center gap-2"
              >
                <Settings className="h-4 w-4 text-muted" />
                个人设置
              </button>
              <button
                onClick={handleLogout}
                role="menuitem"
                className="w-full text-left px-3 py-2 text-sm text-error hover:bg-error/5 transition-colors cursor-pointer flex items-center gap-2"
              >
                <LogOut className="h-4 w-4" />
                退出登录
              </button>
            </div>
          )}
        </div>
      </div>

      <ChangePasswordModal open={changePasswordOpen} onClose={() => setChangePasswordOpen(false)} />
    </header>
  );
}
