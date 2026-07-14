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
  previous_audit_id?: string;
  evolution_context?: string;
}

// ── Subscription / Evolution tracking ────────────────────────────────────────

export interface CronTriggerConfig {
  interval_days: number;
  run_at?: string; // HH:MM UTC
}

export interface KeywordTriggerConfig {
  brand_aliases: string[];
  signal_words: string[];
  poll_interval_hours: number;
}

export interface Trigger {
  type: 'keyword' | 'cron' | 'webhook' | 'news';
  config: CronTriggerConfig | KeywordTriggerConfig | Record<string, unknown>;
}

export interface NotifyTarget {
  type: 'webhook' | 'email' | 'mcp-push';
  url?: string;
  address?: string;
}

export interface Subscription {
  id: string;
  brand: string;
  brand_slug: string;
  panel: string;
  triggers: Trigger[];
  notify: NotifyTarget[];
  cadence: {
    min_interval_days: number;
    max_per_month: number;
  };
  created_at: string;
  last_triggered_at?: string;
  last_audit_id?: string;
  trigger_count_this_month: number;
  month_reset_at: string;
  active: boolean;
}

export interface SubscribeBrandInput {
  brand: string;
  panel?: string;
  triggers?: Array<{ type: string; config?: Record<string, unknown> }>;
  notify?: Array<{ type: string; url?: string; address?: string }>;
  min_interval_days?: number;
  max_per_month?: number;
}

export interface SubscribeBrandOutput {
  subscription_id: string;
  brand: string;
  panel: string;
  triggers: Trigger[];
  message: string;
}

export interface TriggerEvolutionInput {
  brand: string;
  event_type?: string;
  event_summary?: string;
  source_url?: string;
  force?: boolean;
}

export interface TriggerEvolutionOutput {
  audit_id: string;
  phase: AuditPhase;
  message: string;
  skipped?: boolean;
  skip_reason?: string;
}

export interface ListSubscriptionsOutput {
  subscriptions: Array<{
    subscription_id: string;
    brand: string;
    panel: string;
    triggers: Trigger[];
    active: boolean;
    last_triggered_at?: string;
    last_audit_id?: string;
  }>;
}

export interface UnsubscribeBrandInput {
  subscription_id: string;
}

export interface UnsubscribeBrandOutput {
  unsubscribed: boolean;
  subscription_id: string;
}

// ── Scores / Delta reports ───────────────────────────────────────────────────

export interface JudgeScores {
  judge: string;
  lenses: Record<string, number>;
  total: number;
}

export interface AuditScores {
  audit_id: string;
  brand: string;
  generated_at: string;
  judges: JudgeScores[];
  means: Record<string, number>;
  overall_mean: number;
}

export interface LensDelta {
  lens: string;
  old_mean: number;
  new_mean: number;
  delta: number;
}

export interface GetDeltaReportInput {
  audit_id: string;
  previous_audit_id?: string;
  narrative?: boolean;
}

export interface GetDeltaReportOutput {
  audit_id: string;
  previous_audit_id: string;
  brand: string;
  overall_delta: number;
  lens_deltas: LensDelta[];
  delta_markdown: string;
  narrative?: string;
}

// ── Notifications ────────────────────────────────────────────────────────────

export interface NotifyPayload {
  event: string;
  brand: string;
  audit_id: string;
  previous_audit_id?: string;
  overall_delta?: number;
  summary: string;
  delta_markdown?: string;
}

export interface NotifyResult {
  target: string;
  ok: boolean;
  detail?: string;
}

// ── Panels discovery ─────────────────────────────────────────────────────────

export interface ListPanelsOutput {
  panels: Array<{
    name: string;
    display_name: string;
    description: string;
    judges: Array<{ slug: string; name_cn: string; name_en: string; language: string }>;
  }>;
}

// ── Brand trend (trajectory across N audits) ─────────────────────────────────

export interface BrandTrendPoint {
  audit_id: string;
  date: string;
  panel: string;
  overall_mean: number;
  lens_means: Record<string, number>;
}

export interface GetBrandTrendInput {
  brand: string;
}

export interface GetBrandTrendOutput {
  brand: string;
  count: number;
  points: BrandTrendPoint[];
  overall_delta: number;
  trend: 'up' | 'down' | 'flat';
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
  panel?: string;
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

export interface ResumeAuditInput {
  audit_id: string;
  max_cost_usd?: number;
}

export interface ResumeAuditOutput {
  audit_id: string;
  phase: AuditPhase;
  resumed_from: AuditPhase;
  resume_point: AuditPhase;
  message: string;
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

// ── Brand Watch(舆情监控,docs/15)──────────────────────────────────────────

export interface WatchEvent {
  id: string;
  date: string; // YYYY-MM-DD
  dim: string; // W1..W9
  severity: string; // P0..P3
  direction: string; // pos | neg | neutral | mixed
  direction_by: 'model-judged';
  title: string;
  quote: string; // 逐字引用,≤100 字
  quote_type?: string; // title | body
  url: string;
  fetched_at: string; // ISO UTC
  lens_map: string[]; // ⊆ {origin, category, leverage, identity, signal}
  note?: string;
  consumed_by?: string; // vN — 只在审计消费时标记,record 工具不可写
  // ── 舆情驾驶舱扩展字段(可选,docs/20)──
  related_persons?: string[]; // 关联人物(管理层/关键人物)
  source_type?: string; // official|media|finance|social|investor_community|search|regulator
  suggested_action?: string; // 建议动作(结构化;note 仍留作长文)
  alert_tier?: string; // L1|L2|L3 预警层级覆写(缺省由 severity+触发规则推导)
}

export interface WatchTriggerEvaluation {
  as_of: string;
  window_days: number;
  include_consumed: boolean;
  p0: number;
  p1: number;
  p2: number;
  weighted: number;
  rules_hit: string[];
  hit: boolean;
  recommendation: string;
}

export interface GetWatchEventsInput {
  brand: string; // 品牌 slug(watch/<slug>/)
  since?: string; // 只返回该日期(含)之后的事件
  dim?: string;
  severity?: string;
  unconsumed_only?: boolean;
}

export interface GetWatchEventsOutput {
  brand: string;
  count: number;
  events: WatchEvent[];
  trigger: WatchTriggerEvaluation;
}

export interface RecordWatchEventInput {
  brand: string;
  event: Omit<WatchEvent, 'id' | 'direction_by' | 'consumed_by'> & { direction_by?: string };
}

export interface RecordWatchEventOutput {
  recorded: boolean;
  id: string;
  brand: string;
  trigger: WatchTriggerEvaluation;
  notified: NotifyResult[];
  message: string;
}

export interface ServerConfig {
  store_dir: string;
  watch_dir: string;
  max_parallel: number;
  max_concurrent_audits: number;
  max_tokens_per_audit_input: number;
  max_tokens_per_audit_output: number;
  max_audit_runtime_ms: number;
  log_level: 'error' | 'warn' | 'info' | 'debug' | 'trace';
}
