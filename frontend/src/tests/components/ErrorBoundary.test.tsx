/**
 * ErrorBoundary 组件测试（Task 33 — P2 收敛）。
 *
 * 覆盖全局错误边界关键行为：
 * - 无错误时正常渲染 children（不干预）
 * - 子组件抛错 → fallback（不白屏）：错误标题 / 提示 / 重新加载按钮 / 返回首页链接
 * - 抛错后不再渲染 children
 * - 自定义 onError 回调被调用（error + errorInfo）
 *
 * 策略：直接 render <ErrorBoundary>，子组件渲染时 throw；React 自身向
 * console.error 记录被捕获的渲染错误 —— 测试中 spy 静音避免噪音。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../../components/ErrorBoundary';

function Bomb(): never {
  throw new Error('boom');
}

describe('ErrorBoundary（全局错误边界）', () => {
  let errSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    errSpy.mockRestore();
    vi.restoreAllMocks();
  });

  it('无错误时正常渲染 children', () => {
    render(
      <ErrorBoundary>
        <div>正常内容</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('正常内容')).toBeInTheDocument();
    expect(screen.queryByText('页面出现异常')).not.toBeInTheDocument();
  });

  it('子组件抛错时展示 fallback（不白屏）', () => {
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    );
    expect(screen.getByText('页面出现异常')).toBeInTheDocument();
    expect(screen.getByText('系统遇到意外错误，请尝试重新加载。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回首页' })).toBeInTheDocument();
  });

  it('抛错后不再渲染 children', () => {
    render(
      <ErrorBoundary>
        <Bomb />
        <div>不应出现的内容</div>
      </ErrorBoundary>
    );
    expect(screen.queryByText('不应出现的内容')).not.toBeInTheDocument();
  });

  it('自定义 onError 回调被调用（error + errorInfo）', () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <Bomb />
      </ErrorBoundary>
    );
    expect(onError).toHaveBeenCalledTimes(1);
    const [error, errorInfo] = onError.mock.calls[0] as [Error, unknown];
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toBe('boom');
    expect(errorInfo).toBeTruthy();
  });
});
