import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** 自定义错误上报回调；缺省时 console.error */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * 全局错误边界（Task 33 — P2 收敛：无 ErrorBoundary）
 *
 * 捕获子树渲染/生命周期错误，避免整页白屏；降级为可恢复 fallback
 * （重新加载 / 返回首页），错误详情经 onError 或 console.error 上报。
 *
 * 注意：不捕获事件处理器、异步回调与 SSR 中的错误（React 官方限制）。
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    } else {
      console.error('[ErrorBoundary] uncaught render error:', error, errorInfo);
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] p-6">
          <h2 className="text-xl font-semibold text-gray-700">页面出现异常</h2>
          <p className="text-gray-500 mt-2">系统遇到意外错误，请尝试重新加载。</p>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={this.handleReload}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              重新加载
            </button>
            <a
              href="/"
              className="px-4 py-2 text-blue-600 border border-blue-600 rounded hover:bg-blue-50"
            >
              返回首页
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
