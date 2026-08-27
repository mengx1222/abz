import { type ReactNode } from 'react';
import { Inbox } from 'lucide-react';
import { cn } from '../../utils/cn';

interface EmptyStateProps {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}

/** 统一空状态：图标 + 标题 + 说明 + 可选操作 */
export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 px-4 text-center', className)}>
      <div className="h-12 w-12 rounded-full bg-surface flex items-center justify-center mb-4">
        {icon ?? <Inbox aria-hidden="true" className="h-5 w-5 text-muted" />}
      </div>
      <p className="text-sm font-medium text-text">{title}</p>
      {description && <p className="text-sm text-muted mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
