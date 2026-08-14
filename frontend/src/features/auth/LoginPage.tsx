import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { useAuthStore } from '../../stores/authStore';
import { useToast } from '../../hooks/useToast';

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const isLoading = useAuthStore((s) => s.isLoading);
  const { toast } = useToast();

  const [phone, setPhone] = useState('13800138000');
  const [code, setCode] = useState('888888');
  const [countdown, setCountdown] = useState(0);

  async function handleSendCode() {
    if (!phone || phone.length !== 11) {
      toast({ title: '请输入正确的手机号', variant: 'warning' });
      return;
    }
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    toast({ title: '验证码已发送', variant: 'success' });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!phone || phone.length !== 11) {
      toast({ title: '请输入正确的手机号', variant: 'warning' });
      return;
    }
    if (!code || code.length < 4) {
      toast({ title: '请输入验证码', variant: 'warning' });
      return;
    }
    try {
      await login(phone, code);
      toast({ title: '登录成功', variant: 'success' });
      navigate('/dashboard');
    } catch (err) {
      toast({ title: '登录失败', description: (err as Error).message, variant: 'error' });
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-[400px]">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary mb-4">
            <span className="text-white font-bold text-2xl">安</span>
          </div>
          <h1 className="text-2xl font-bold text-primary">安诊保 AI 副驾</h1>
          <p className="text-muted text-sm mt-1.5">
            智能保险销售助手，让每一通电话都更专业
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-card rounded-2xl border border-border shadow-sm p-8">
          <h2 className="text-lg font-semibold text-text mb-6">登录</h2>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="手机号"
              type="tel"
              placeholder="请输入手机号"
              value={phone}
              onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 11))}
              maxLength={11}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"
                  />
                </svg>
              }
            />

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium text-text">验证码</label>
                <button
                  type="button"
                  onClick={handleSendCode}
                  disabled={countdown > 0}
                  className="text-xs text-accent hover:text-accent/80 disabled:text-muted disabled:cursor-not-allowed cursor-pointer transition-colors"
                >
                  {countdown > 0 ? `${countdown}s 后重新发送` : '获取验证码'}
                </button>
              </div>
              <input
                type="text"
                placeholder="请输入验证码"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6}
                className="w-full h-10 rounded-lg border border-border bg-white px-3 text-sm text-text placeholder:text-muted/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              />
            </div>

            <Button type="submit" loading={isLoading} className="mt-2 w-full h-11">
              登录
            </Button>
          </form>
        </div>

        {/* Demo hint */}
        <div className="mt-4 text-center">
          <p className="text-xs text-muted bg-card border border-border rounded-lg px-4 py-2.5">
            演示账号：<span className="font-mono text-text">13800138000</span> /{' '}
            <span className="font-mono text-text">888888</span>
          </p>
        </div>

        <p className="text-center text-xs text-muted/60 mt-4">
          © 2024 安诊保 · 智能保险销售平台
        </p>
      </div>
    </div>
  );
}
