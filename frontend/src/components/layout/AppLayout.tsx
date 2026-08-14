import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { cn } from '../../utils/cn';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* Sidebar */}
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar />
        <main className={cn('flex-1 overflow-y-auto p-6', !sidebarCollapsed ? 'ml-0' : 'ml-0')}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}