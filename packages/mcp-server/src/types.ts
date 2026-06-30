export type AuditPhase =
  | 'proposed'
  | 'researching'
  | 'synthesizing'
  | 'judging'
  | 'merging'
  | 'done'
  | 'failed'
  | 'interrupted';

export interface AuditState {
  audit_id: string;
  brand: string;
  brand_slug: string;
  panel: string;
  mode: 'fresh' | 'evolution';
  phase: AuditPhase;
  started_at: string;
  last_progress_at: string;
  completed_phases: string[];
  failed_phases: string[];
  errors: AuditError[];
  tokens_used: { input: number; output: number };
  options: AuditOptions;
}

export interface AuditOptions {
  focus_dimensions?: string[];
  judges?: string[];
  skip_wuying: boolean;
  language: 'zh' | 'en' | 'auto';
  max_cost_usd?: number;
}

export interface AuditError {
  phase: string;
  code: string;
  message: string;
  timestamp: string;
}

export interface ProposeAuditInput {
  brand: string;
  mode?: 'fresh' | 'evolution' | 'auto';
  focus_dimensions?: string[];
  judges?: string[];
  skip_wuying?: boolean;
  language?: 'zh' | 'en' | 'auto';
}

export interface ProposeAuditOutput {
  audit_id: string;
  proposal_markdown: string;
  estimated_runtime_min: number;
  estimated_token_cost_usd: number;
}

export interface ConfirmAuditInput {
  audit_id: string;
  edits?: {
    drop_dimensions?: string[];
    add_dimensions?: string[];
    drop_judges?: string[];
  };
  max_cost_usd?: number;
}

export interface GetStatusOutput {
  audit_id: string;
  brand: string;
  phase: AuditPhase;
  progress_pct: number;
  started_at: string;
  last_progress_at: string;
  completed_phases: string[];
  errors: AuditError[];
  tokens_used: { input: number; output: number };
}

export interface FetchReportInput {
  audit_id: string;
  format?: 'markdown' | 'html' | 'both';
}

export interface FetchReportOutput {
  markdown?: string;
  html?: string;
  version: number;
  generated_at: string;
}

export interface ListAuditsOutput {
  audits: Array<{
    audit_id: string;
    brand: string;
    phase: AuditPhase;
    started_at: string;
    last_progress_at: string;
  }>;
}

export interface AddJudgeInput {
  name: string;
  persona_markdown: string;
  validate_only?: boolean;
}

export interface AddJudgeOutput {
  registered: boolean;
  validation: {
    has_anti_fabrication: boolean;
    has_decision_heuristics: boolean;
    warnings: string[];
  };
}

export interface ServerConfig {
  store_dir: string;
  max_parallel: number;
  max_concurrent_audits: number;
  max_tokens_per_audit_input: number;
  max_tokens_per_audit_output: number;
  max_audit_runtime_ms: number;
  log_level: 'error' | 'warn' | 'info' | 'debug' | 'trace';
}
