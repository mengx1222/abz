import { useEffect } from 'react';
import { X, CheckCircle2, XCircle, AlertTriangle, Info } from 'lucide-react';
import { useToastStore, type Toast } from '../../hooks/useToast';
import { cn } from '../../utils/cn';

const variantStyles: Record<string, string> = {
  default: 'border-border',
  success: 'border-success/30',
  error: 'border-error/30',
  warning: 'border-warning/30',
};

const iconMap: Record<string, React.ReactNode> = {
  default: <Info className="h-4 w-4 text-accent mt-0.5 flex-shrink-0" />,
  success: <CheckCircle2 className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />,
  error: <XCircle className="h-4 w-4 text-error mt-0.5 flex-shrink-0" />,
  warning: <AlertTriangle className="h-4 w-4 text-warning mt-0.5 flex-shrink-0" />,
};

function ToastItem({ toast }: { toast: Toast }) {
  const removeToast = useToastStore((s) => s.removeToast);

  useEffect(() => {
    const timer = setTimeout(() => removeToast(toast.id), toast.duration ?? 3000);
    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, removeToast]);

  return (
    <div
      role="status"
      className={cn(
        'flex items-start gap-3 rounded-lg border bg-card px-4 py-3 shadow-pop min-w-[320px] max-w-[420px] animate-slide-in-right',
        variantStyles[toast.variant || 'default']
      )}
    >
      {iconMap[toast.variant || 'default']}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text">{toast.title}</p>
        {toast.description && (
          <p className="text-xs text-muted mt-0.5">{toast.description}</p>
        )}
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        aria-label="关闭"
        className="text-muted hover:text-text transition-colors cursor-pointer"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[70] flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
