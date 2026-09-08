import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Smartphone, KeyRound } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { useAuthStore } from '../../stores/authStore';
import { useToast } from '../../hooks/useToast';
import { fetchAuthMode } from '../../services/authService';

const DEMO_USERS = [
  { phone: '13800138000', name: '张张', role: '代理人', desc: '一线销售' },
  { phone: '13800138001', name: '罗罗', role: '团队长', desc: '团队管理' },
  { phone: '13800138002', name: '噜噜', role: '分公司管理员', desc: '分公司运营' },
  { phone: '13800138003', name: '噜妹', role: '系统管理员', desc: '系统管理' },
];

type AuthMode = 'loading' | 'demo' | 'password';

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const isLoading = useAuthStore((s) => s.isLoading);
  const { toast } = useToast();

  const [authMode, setAuthMode] = useState<AuthMode>('loading');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [countdown, setCountdown] = useState(0);

  // 按后端运行模式选择登录表单：demo=验证码+快捷登录，生产=密码
  useEffect(() => {
    let active = true;
    fetchAuthMode().then((mode) => {
      if (!active) return;
      setAuthMode(mode);
      // demo 模式预填演示账号，减少输入
      if (mode === 'demo') {
        setPhone('13800138000');
        setCode('888888');
      }
    });
    return () => {
      active = false;
    };
  }, []);

  function handleSendCode() {
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

  async function doLogin(credentials: { phone: string; verification_code?: string; password?: string }) {
    try {
      await login(credentials);
      toast({ title: '登录成功', variant: 'success' });
      navigate('/dashboard');
    } catch (err) {
      toast({ title: '登录失败', description: (err as Error).message, variant: 'error' });
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!phone || phone.length !== 11) {
      toast({ title: '请输入正确的手机号', variant: 'warning' });
      return;
    }
    if (authMode === 'password') {
      if (!password) {
        toast({ title: '请输入密码', variant: 'warning' });
        return;
      }
      await doLogin({ phone, password });
      return;
    }
    if (!code || code.length < 4) {
      toast({ title: '请输入验证码', variant: 'warning' });
      return;
    }
    await doLogin({ phone, verification_code: code });
  }

  function handleDemoLogin(demoPhone: string) {
    // Auto-login on next frame（密码字段在 demo 与生产两模式后端均接受 888888）
    setTimeout(async () => {
      await doLogin({ phone: demoPhone, password: '888888' });
    }, 0);
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-[420px]">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent mb-4">
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

          {authMode === 'loading' ? (
            <div className="flex items-center justify-center py-10">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <Input
                label="手机号"
                type="tel"
                placeholder="请输入手机号"
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 11))}
                maxLength={11}
                icon={<Smartphone className="w-4 h-4" />}
              />

              {authMode === 'demo' ? (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-sm font-medium text-text">验证码</label>
                    <button
                      type="button"
                      onClick={handleSendCode}
                      disabled={countdown > 0}
                      className="text-xs text-accent hover:text-accent-hover disabled:text-muted disabled:cursor-not-allowed cursor-pointer transition-colors"
                    >
                      {countdown > 0 ? `${countdown}s 后重新发送` : '获取验证码'}
                    </button>
                  </div>
                  <Input
                    type="text"
                    placeholder="请输入验证码"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    maxLength={6}
                    icon={<KeyRound className="w-4 h-4" />}
                  />
                </div>
              ) : (
                <Input
                  label="密码"
                  type="password"
                  placeholder="请输入密码"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  icon={<KeyRound className="w-4 h-4" />}
                />
              )}

              <Button type="submit" loading={isLoading} className="mt-2 w-full h-11">
                登录
              </Button>
            </form>
          )}
        </div>

        {/* Demo user quick-switch（始终显示：生产模式演示账号已入库，密码登录） */}
        <div className="mt-4">
          <p className="text-xs text-muted mb-2 text-center">演示账号快捷登录</p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_USERS.map((u) => (
              <button
                key={u.phone}
                type="button"
                onClick={() => handleDemoLogin(u.phone)}
                disabled={isLoading}
                className="flex items-center gap-2.5 bg-card border border-border rounded-lg px-3 py-2.5 hover:border-accent/40 hover:shadow-sm transition-all duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed text-left"
              >
                <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
                  <span className="text-accent text-xs font-bold">
                    {u.name.charAt(0)}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text truncate">{u.name}</p>
                  <p className="text-[11px] text-muted truncate">{u.role} · {u.desc}</p>
                </div>
              </button>
            ))}
          </div>
          <p className="text-[11px] text-muted/50 text-center mt-2">
            统一密码：<span className="font-mono">888888</span>
          </p>
        </div>

        <p className="text-center text-xs text-muted/60 mt-4">
          © 2026 华安保险 · 安诊保 AI 副驾
        </p>
      </div>
    </div>
  );
}
