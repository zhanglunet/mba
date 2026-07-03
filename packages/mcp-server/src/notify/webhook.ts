import type { NotifyPayload } from '../types.js';

const TIMEOUT_MS = 10_000;

/**
 * POST the payload as JSON to a webhook URL. Returns { ok, detail }.
 * Never throws — network failures are captured into the result.
 */
export async function sendWebhook(
  url: string,
  payload: NotifyPayload,
): Promise<{ ok: boolean; detail?: string }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!res.ok) {
      return { ok: false, detail: `HTTP ${res.status}` };
    }
    return { ok: true, detail: `HTTP ${res.status}` };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { ok: false, detail: msg };
  } finally {
    clearTimeout(timer);
  }
}
