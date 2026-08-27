import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';
import { Modal } from './Modal';

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  loading?: boolean;
}

/** 统一的破坏性/重要操作确认弹窗，替代各页 window.confirm */
export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = '确认',
  cancelText = '取消',
  danger = true,
  loading = false,
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onClose} size="sm">
      <div className="flex items-start gap-4 pr-4">
        <div
          className={
            danger
              ? 'flex-shrink-0 h-10 w-10 rounded-full bg-error/10 flex items-center justify-center'
              : 'flex-shrink-0 h-10 w-10 rounded-full bg-accent/10 flex items-center justify-center'
          }
        >
          <AlertTriangle className={danger ? 'h-5 w-5 text-error' : 'h-5 w-5 text-accent'} />
        </div>
        <div className="min-w-0 pt-0.5">
          <h2 className="text-base font-semibold text-text">{title}</h2>
          {message && <p className="text-sm text-muted mt-1.5 leading-relaxed">{message}</p>}
        </div>
      </div>
      <div className="flex justify-end gap-3 mt-6">
        <Button variant="secondary" size="sm" onClick={onClose} disabled={loading}>
          {cancelText}
        </Button>
        <Button variant={danger ? 'danger' : 'primary'} size="sm" onClick={onConfirm} loading={loading}>
          {confirmText}
        </Button>
      </div>
    </Modal>
  );
}
