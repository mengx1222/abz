/**
 * AI 等待态提示：流式开始前尚无内容时展示「正在思考」+ 三点跳动。
 * 用于产品问答页与全局 AI 助手的空回复气泡（有内容后替换为逐字光标）。
 */
export function ThinkingIndicator() {
  return (
    <span className="inline-flex items-center gap-1.5 text-muted text-sm" role="status" aria-label="正在思考">
      <span>正在思考</span>
      <span className="inline-flex gap-0.5">
        <span className="h-1 w-1 rounded-full bg-muted animate-bounce" />
        <span className="h-1 w-1 rounded-full bg-muted animate-bounce [animation-delay:120ms]" />
        <span className="h-1 w-1 rounded-full bg-muted animate-bounce [animation-delay:240ms]" />
      </span>
    </span>
  );
}
