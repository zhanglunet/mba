import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'yaml';
import type { WatchEvent } from '../types.js';

/**
 * Brand Watch 数据层(watch/<slug>/events.yaml + watch/matrix.yaml)。
 *
 * 与 Python 侧 scripts/watch-tools/validate_watch.py 是同一套规则的镜像:
 * 事实字段可溯源(url/quote/date/fetched_at)、判断字段恒标 model-judged、
 * quote ≤ 100 字、dim 不得落在矩阵 off 维度上。record 侧新增事件**只追加**
 * 原文件文本(保留注释与既有格式),不整体重写。
 */

export const DIMS = new Set(['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9']);
export const SEVERITIES = new Set(['P0', 'P1', 'P2', 'P3']);
export const DIRECTIONS = new Set(['pos', 'neg', 'neutral', 'mixed']);
export const LENSES = new Set(['origin', 'category', 'leverage', 'identity', 'signal']);
export const QUOTE_TYPES = new Set(['title', 'body']);
// 舆情驾驶舱扩展字段枚举(docs/20;镜像 validate_watch.py)。
export const SOURCE_TYPES = new Set([
  'official', 'media', 'finance', 'social', 'investor_community', 'search', 'regulator',
]);
export const ALERT_TIERS = new Set(['L1', 'L2', 'L3']);
export const QUOTE_MAX = 100;

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const FETCHED_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z$/;

function normFlag(v: unknown): string {
  // YAML 1.1 会把 on/off 解析成布尔(过程记录见 docs/16 §2.4)。
  if (v === true) return 'on';
  if (v === false) return 'off';
  return String(v);
}

function toDateString(v: unknown): string {
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  return String(v ?? '');
}

export class WatchStore {
  constructor(private readonly watchDir: string) {}

  matrixPath(): string {
    return join(this.watchDir, 'matrix.yaml');
  }

  eventsPath(slug: string): string {
    return join(this.watchDir, slug, 'events.yaml');
  }

  /** 读适用性矩阵:slug → { W1..W9: core|on|off }。矩阵缺失返回 null。 */
  async readMatrix(): Promise<Record<string, Record<string, string>> | null> {
    const path = this.matrixPath();
    if (!existsSync(path)) return null;
    const raw = parse(await readFile(path, 'utf-8')) as { brands?: Record<string, Record<string, unknown>> };
    const out: Record<string, Record<string, string>> = {};
    for (const [slug, dims] of Object.entries(raw?.brands ?? {})) {
      out[slug] = Object.fromEntries(Object.entries(dims).map(([d, v]) => [d, normFlag(v)]));
    }
    return out;
  }

  /** 读单品牌事件流(date 归一化为 YYYY-MM-DD 字符串)。文件不存在返回 []。 */
  async readEvents(slug: string): Promise<WatchEvent[]> {
    const path = this.eventsPath(slug);
    if (!existsSync(path)) return [];
    const parsed = parse(await readFile(path, 'utf-8'));
    if (!Array.isArray(parsed)) return [];
    return parsed.map((e: Record<string, unknown>) => ({
      ...e,
      date: toDateString(e['date']),
    })) as WatchEvent[];
  }

  /** 下一个事件 id:<date>-<slug>-NNN,NNN 为全文件最大序号 +1。 */
  nextEventId(events: WatchEvent[], slug: string, date: string): string {
    let max = 0;
    for (const e of events) {
      const m = /-(\d{3})$/.exec(String(e.id ?? ''));
      if (m) max = Math.max(max, Number(m[1]));
    }
    return `${date}-${slug}-${String(max + 1).padStart(3, '0')}`;
  }

  /**
   * 校验一条待录入事件(镜像 validate_watch.py 检查 A/B/C)。
   * 返回违规列表;空列表 = 合法。record 工具不接受 consumed_by(审计时才标)。
   */
  validateNewEvent(
    slug: string,
    e: Omit<WatchEvent, 'id'>,
    matrix: Record<string, Record<string, string>> | null,
  ): string[] {
    const errs: string[] = [];
    if (matrix && !(slug in matrix)) {
      errs.push(`品牌 \`${slug}\` 不在适用性矩阵(先补 watch/matrix.yaml)`);
    }
    if (!DATE_RE.test(e.date)) errs.push(`date \`${e.date}\` 不是合法 YYYY-MM-DD`);
    else if (e.date > new Date().toISOString().slice(0, 10)) errs.push(`date ${e.date} 在未来`);
    if (!DIMS.has(e.dim)) errs.push(`dim \`${e.dim}\` 非法(W1..W9)`);
    else if (matrix?.[slug]?.[e.dim] === 'off') {
      errs.push(`dim ${e.dim} 在 \`${slug}\` 上为 off(空维度诚实留空,不许填事件)`);
    }
    if (!SEVERITIES.has(e.severity)) errs.push(`severity \`${e.severity}\` 非法(P0..P3)`);
    if (!DIRECTIONS.has(e.direction)) errs.push(`direction \`${e.direction}\` 非法(pos/neg/neutral/mixed)`);
    if (e.direction_by !== 'model-judged') {
      errs.push('direction_by 必须为 model-judged(判断字段不得伪装成事实)');
    }
    if (!e.title) errs.push('缺 title');
    if (!e.quote) errs.push('缺 quote(逐字引用是可溯源底线)');
    else if (e.quote.length > QUOTE_MAX) {
      errs.push(`quote 超 ${QUOTE_MAX} 字(${e.quote.length})——只存短逐字引用 + 链接原文`);
    }
    if (!QUOTE_TYPES.has(e.quote_type ?? '')) errs.push(`quote_type \`${e.quote_type}\` 非法(title/body)`);
    if (!/^https?:\/\//.test(e.url ?? '')) errs.push('url 必须是 http(s) 绝对地址');
    if (!FETCHED_RE.test(e.fetched_at ?? '')) {
      errs.push(`fetched_at \`${e.fetched_at}\` 应为 ISO UTC(YYYY-MM-DDTHH:MM[:SS]Z)`);
    }
    if (!Array.isArray(e.lens_map) || e.lens_map.length === 0 || !e.lens_map.every(l => LENSES.has(l))) {
      errs.push(`lens_map 必须是非空列表且 ⊆ ${[...LENSES].sort().join('/')}`);
    }
    if ((e as WatchEvent).consumed_by !== undefined) {
      errs.push('consumed_by 不可经 record_watch_event 写入(只在审计消费时标记)');
    }
    // ── 舆情驾驶舱扩展字段(可选,docs/20)──
    const ev = e as WatchEvent;
    if (ev.source_type !== undefined && !SOURCE_TYPES.has(ev.source_type)) {
      errs.push(`source_type \`${ev.source_type}\` 非法(${[...SOURCE_TYPES].join('/')})`);
    }
    if (ev.alert_tier !== undefined && !ALERT_TIERS.has(ev.alert_tier)) {
      errs.push(`alert_tier \`${ev.alert_tier}\` 非法(L1/L2/L3)`);
    }
    if (ev.related_persons !== undefined
        && (!Array.isArray(ev.related_persons) || !ev.related_persons.every(x => typeof x === 'string'))) {
      errs.push('related_persons 必须是字符串列表');
    }
    if (ev.suggested_action !== undefined && typeof ev.suggested_action !== 'string') {
      errs.push('suggested_action 必须是字符串');
    }
    return errs;
  }

  /** 追加事件:只在文件尾追加 YAML 文本块,不重写既有内容(保注释)。 */
  async appendEvent(slug: string, event: WatchEvent): Promise<void> {
    const path = this.eventsPath(slug);
    const q = (s: string) => `"${s.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
    const lines = [
      `- id: ${event.id}`,
      `  date: ${event.date}`,
      `  dim: ${event.dim}`,
      `  severity: ${event.severity}`,
      `  direction: ${event.direction}`,
      `  direction_by: model-judged`,
      `  title: ${q(event.title)}`,
      `  quote: ${q(event.quote)}`,
      `  quote_type: ${event.quote_type}`,
      `  url: ${event.url}`,
      `  fetched_at: ${q(event.fetched_at)}`,
      `  lens_map: [${event.lens_map.join(', ')}]`,
    ];
    if (event.related_persons?.length) {
      lines.push(`  related_persons: [${event.related_persons.map(q).join(', ')}]`);
    }
    if (event.source_type) lines.push(`  source_type: ${event.source_type}`);
    if (event.suggested_action) lines.push(`  suggested_action: ${q(event.suggested_action)}`);
    if (event.alert_tier) lines.push(`  alert_tier: ${event.alert_tier}`);
    if (event.note) lines.push(`  note: ${q(event.note)}`);
    const block = lines.join('\n') + '\n';

    if (!existsSync(path)) {
      await mkdir(join(this.watchDir, slug), { recursive: true });
      const header = `# watch/${slug}/events.yaml — 舆情事件流(schema 见 docs/16 §2)\n\n`;
      await writeFile(path, header + block, 'utf-8');
      return;
    }
    const existing = await readFile(path, 'utf-8');
    const sep = existing.endsWith('\n\n') ? '' : existing.endsWith('\n') ? '\n' : '\n\n';
    await writeFile(path, existing + sep + block, 'utf-8');
  }
}
