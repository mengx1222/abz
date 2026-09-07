import { useState, type FormEvent } from 'react';
import { KeyRound } from 'lucide-react';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { useToast } from '../../hooks/useToast';
import { getApiErrorMessage } from '../../utils/apiError';
import { changePassword } from '../../services/authService';

interface ChangePasswordModalProps {
  open: boolean;
  onClose: () => void;
}

export function ChangePasswordModal({ open, onClose }: ChangePasswordModalProps) {
  const { toast } = useToast();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function reset() {
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setFormError(null);
  }

  function handleClose() {
    if (submitting) return;
    reset();
    onClose();
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (newPassword.length < 8) {
      setFormError('新密码至少需要 8 位');
      return;
    }
    if (newPassword === oldPassword) {
      setFormError('新密码不能与原密码相同');
      return;
    }
    if (newPassword !== confirmPassword) {
      setFormError('两次输入的新密码不一致');
      return;
    }

    setSubmitting(true);
    try {
      const message = await changePassword(oldPassword, newPassword);
      toast({ title: message || '密码修改成功', variant: 'success' });
      reset();
      onClose();
    } catch (err) {
      setFormError(getApiErrorMessage(err, '密码修改失败，请稍后重试'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="修改密码"
      description="建议密码长度 8 位以上，包含字母和数字。修改成功后请使用新密码重新登录。"
      size="sm"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="原密码"
          type="password"
          autoComplete="current-password"
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
          placeholder="请输入当前使用的密码"
          required
        />
        <Input
          label="新密码"
          type="password"
          autoComplete="new-password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="至少 8 位"
          error={formError ?? undefined}
          required
        />
        <Input
          label="确认新密码"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="再次输入新密码"
          required
        />
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose} disabled={submitting}>
            取消
          </Button>
          <Button type="submit" loading={submitting} disabled={!oldPassword || !newPassword || !confirmPassword}>
            <span className="flex items-center gap-1.5">
              <KeyRound className="h-4 w-4" />
              确认修改
            </span>
          </Button>
        </div>
      </form>
    </Modal>
  );
}
