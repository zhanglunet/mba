const RESEND_ENDPOINT = 'https://api.resend.com/emails';
const TIMEOUT_MS = 10_000;

/**
 * Send an email via the Resend API. Requires MBA_RESEND_API_KEY and MBA_NOTIFY_FROM.
 * If not configured, returns { ok: false, detail: 'not configured' } without throwing.
 */
export async function sendEmail(
  to: string,
  subject: string,
  body: string,
): Promise<{ ok: boolean; detail?: string }> {
  const apiKey = process.env['MBA_RESEND_API_KEY'];
  const from = process.env['MBA_NOTIFY_FROM'];
  if (!apiKey || !from) {
    return { ok: false, detail: 'email not configured (set MBA_RESEND_API_KEY + MBA_NOTIFY_FROM)' };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(RESEND_ENDPOINT, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ from, to, subject, text: body }),
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
