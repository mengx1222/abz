/**
 * API 错误消息提取工具（Task 24 — P2-2 统一 401/403 语义）。
 *
 * 后端错误响应存在两种格式（审计证据，docs/p2-hardening-audit.md P2-2）：
 * 1. 统一 ErrorResponse（login/refresh 等手动构造）：
 *      { success: false, error: { code, message }, request_id }
 * 2. FastAPI HTTPException（get_current_user 等依赖抛出的 401/403/404）：
 *      { detail: { code, message } }
 *
 * 本工具按「error.message 优先、detail.message 次之」提取真实后端消息，
 * 供登录失败、页面错误 toast 等场景展示（不再吞成固定文案）。
 */

interface ApiErrorShape {
  response?: {
    data?: {
      error?: { message?: string };
      detail?: { message?: string };
    };
  };
}

export function getApiErrorMessage(err: unknown, fallback = '操作失败'): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as ApiErrorShape).response?.data;
    if (data) {
      const fromError = data.error?.message;
      if (fromError) return fromError;
      const fromDetail = data.detail?.message;
      if (fromDetail) return fromDetail;
    }
  }
  return fallback;
}
