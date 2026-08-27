import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { CitationItem, ComplianceResult } from '../../services/salesAgentService';

// ---- AI 助手对话的共享展示件（SalesAgentPage 与全局 AssistantDrawer 复用） ----

export interface AgentMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolLog: string[];
  citations: CitationItem[];
  compliance: ComplianceResult | null;
  ragStatus: string | null;
  status: 'streaming' | 'completed' | 'refused' | 'error';
  errorMessage?: string;
}

export function formatScore(score?: number): string {
  if (score === undefined || score === null) return '';
  return `（${Math.round(score * 100)}%）`;
}

// ---- 合规面板（真实绑定后端结果） ----

export const COMPLIANCE_META: Record<
  ComplianceResult['status'],
  { variant: 'success' | 'warning' | 'danger'; label: string; hint: string }
> = {
  GREEN: { variant: 'success', label: '合规通过', hint: '合规检查通过，内容可正常使用。' },
  YELLOW: { variant: 'warning', label: '建议人工确认', hint: '存在需要人工确认的表述，请修改或复核后再使用。' },
  RED: { variant: 'danger', label: '禁止直接对客使用', hint: '检测到违规表述，该内容不可直接用于客户沟通。' },
};

export function CompliancePanel({ compliance }: { compliance: ComplianceResult | null }) {
  if (!compliance) return null;
  const meta = COMPLIANCE_META[compliance.status] || COMPLIANCE_META.GREEN;
  return (
    <div className="mt-3 rounded-xl border border-border bg-bg/60 p-3">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-xs font-medium text-muted">合规检查</span>
        <Badge variant={meta.variant}>{meta.label}</Badge>
      </div>
      <p className="text-xs text-muted">{meta.hint}</p>
      {compliance.issues && compliance.issues.length > 0 && (
        <ul className="mt-2 space-y-1">
          {compliance.issues.slice(0, 5).map((issue, i) => (
            <li key={i} className="text-xs text-muted flex gap-1.5">
              <span>·</span>
              <span>
                {issue.rule}
                {issue.suggestion ? `：${issue.suggestion}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---- 引用面板（📖/📄 文案被 e2e 断言，勿改） ----

export function CitationPanel({ citations }: { citations: CitationItem[] }) {
  if (!citations || citations.length === 0) return null;
  return (
    <div className="mt-3 rounded-xl border border-border bg-bg/60 p-3">
      <p className="text-xs font-medium text-muted mb-2">📖 产品知识来源</p>
      <div className="flex flex-wrap gap-2">
        {citations.map((c, i) => (
          <div
            key={i}
            className="flex items-center gap-1.5 text-xs bg-card border border-border rounded-lg px-2.5 py-1.5"
          >
            <span className="text-accent">📄</span>
            <span className="text-text">{c.document_title || '未知文档'}</span>
            {c.section ? <span className="text-muted">· {c.section}</span> : null}
            {formatScore(c.score) && <span className="text-muted">{formatScore(c.score)}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- 工具执行状态（仅安全状态说明，不暴露内部 prompt/reasoning） ----

export function ToolStatusLog({ log }: { log: string[] }) {
  if (log.length === 0) return null;
  return (
    <div className="mt-2 space-y-0.5">
      {log.map((step, i) => (
        <div key={i} className="flex items-center gap-1.5 text-xs text-muted">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent/60" />
          <span>{step}</span>
        </div>
      ))}
    </div>
  );
}

// ---- 折叠的工具执行轨迹行内错误+重试块 ----

export function AgentErrorBlock({
  message,
  onRetry,
  retryDisabled,
}: {
  message?: string;
  onRetry: () => void;
  retryDisabled?: boolean;
}) {
  return (
    <div className="mt-3 rounded-lg bg-error/10 border border-error/30 px-3 py-2">
      <p className="text-xs text-error font-medium">{message || '服务异常，请稍后重试。'}</p>
      <Button variant="secondary" size="sm" className="mt-2" onClick={onRetry} disabled={retryDisabled}>
        重试
      </Button>
    </div>
  );
}
