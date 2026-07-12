import type { NotifyTarget, NotifyPayload, NotifyResult } from '../types.js';
import { sendWebhook } from './webhook.js';
import { sendEmail } from './email.js';

/**
 * Deliver a notification payload to every target in a subscription.
 * Each target is attempted independently; a failure on one does not
 * block the others. Returns a per-target result list. Never throws.
 */
export async function dispatchNotifications(
  targets: NotifyTarget[],
  payload: NotifyPayload,
  log: (level: string, msg: string) => void,
): Promise<NotifyResult[]> {
  const results: NotifyResult[] = [];

  for (const target of targets) {
    if (target.type === 'webhook') {
      if (!target.url) {
        results.push({ target: 'webhook', ok: false, detail: 'missing url' });
        continue;
      }
      const r = await sendWebhook(target.url, payload);
      results.push({ target: `webhook:${target.url}`, ok: r.ok, detail: r.detail });
      log(r.ok ? 'info' : 'warn', `[notify] webhook ${target.url}: ${r.ok ? 'ok' : 'failed'} (${r.detail})`);
    } else if (target.type === 'email') {
      if (!target.address) {
        results.push({ target: 'email', ok: false, detail: 'missing address' });
        continue;
      }
      const subject = payload.event === 'watch_alert'
        ? `MBA watch — ${payload.brand} 建议重审`
        : `MBA delta — ${payload.brand} (${signed(payload.overall_delta)})`;
      const body = buildEmailBody(payload);
      const r = await sendEmail(target.address, subject, body);
      results.push({ target: `email:${target.address}`, ok: r.ok, detail: r.detail });
      log(r.ok ? 'info' : 'warn', `[notify] email ${target.address}: ${r.ok ? 'ok' : 'failed'} (${r.detail})`);
    } else if (target.type === 'mcp-push') {
      // mcp-push is served passively via get_status polling — nothing to send.
      results.push({ target: 'mcp-push', ok: true, detail: 'served via get_status' });
    } else {
      results.push({ target: String(target.type), ok: false, detail: 'unknown target type' });
    }
  }

  return results;
}

function signed(n?: number): string {
  if (n === undefined) return 'n/a';
  return n >= 0 ? `+${n}` : `${n}`;
}

function buildEmailBody(payload: NotifyPayload): string {
  const lines = [
    payload.summary,
    '',
    `Brand: ${payload.brand}`,
    `Audit: ${payload.audit_id}`,
  ];
  if (payload.previous_audit_id) lines.push(`Baseline: ${payload.previous_audit_id}`);
  if (payload.delta_markdown) {
    lines.push('', '---', '', payload.delta_markdown);
  }
  return lines.join('\n');
}
