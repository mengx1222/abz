import { useEffect } from 'react';
import { useToastStore, type Toast } from '../../hooks/useToast';
import { cn } from '../../utils/cn';

const variantStyles: Record<string, string> = {
  default: 'bg-white border-border',
  success: 'bg-white border-success/30',
  error: 'bg-white border-error/30',
  warning: 'bg-white border-warning/30',
};

const iconMap: Record<string, string> = {
  default: 'ℹ️',
  success: '✅',
  error: '❌',
  warning: '⚠️',
};

function ToastItem({ toast }: { toast: Toast }) {
  const removeToast = useToastStore((s) => s.removeToast);

  useEffect(() => {
    const timer = setTimeout(() => removeToast(toast.id), toast.duration ?? 3000);
    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, removeToast]);

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg min-w-[320px] max-w-[420px] animate-in slide-in-from-right',
        variantStyles[toast.variant || 'default']
      )}
    >
      <span className="text-sm mt-0.5">{iconMap[toast.variant || 'default']}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text">{toast.title}</p>
        {toast.description && (
          <p className="text-xs text-muted mt-0.5">{toast.description}</p>
        )}
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        className="text-muted hover:text-text text-sm leading-none cursor-pointer"
      >
        ✕
      </button>
    </div>
  );
}

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
