import { type ReactNode } from 'react';
import { cn } from '../../utils/cn';

export interface TabItem {
  key: string;
  label: ReactNode;
}

interface TabsProps {
  items: TabItem[];
  active: string;
  onChange: (key: string) => void;
  variant?: 'underline' | 'pill';
  className?: string;
}

/** 全应用统一的 Tab 组件：underline 用于页面级切换，pill 用于紧凑过滤 */
export function Tabs({ items, active, onChange, variant = 'underline', className }: TabsProps) {
  if (variant === 'pill') {
    return (
      <div
        role="tablist"
        className={cn('inline-flex items-center gap-1 rounded-lg bg-surface p-1', className)}
      >
        {items.map((item) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={active === item.key}
            onClick={() => onChange(item.key)}
            className={cn(
              'h-8 px-3.5 rounded-md text-sm font-medium transition-all duration-150 cursor-pointer whitespace-nowrap',
              active === item.key
                ? 'bg-card text-text shadow-xs'
                : 'text-muted hover:text-text'
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div
      role="tablist"
      className={cn('flex items-center gap-1 border-b border-border', className)}
    >
      {items.map((item) => (
        <button
          key={item.key}
          role="tab"
          aria-selected={active === item.key}
          onClick={() => onChange(item.key)}
          className={cn(
            'relative -mb-px h-9 px-3.5 text-sm font-medium border-b-2 transition-colors duration-150 cursor-pointer whitespace-nowrap',
            active === item.key
              ? 'border-accent text-accent'
              : 'border-transparent text-muted hover:text-text'
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
