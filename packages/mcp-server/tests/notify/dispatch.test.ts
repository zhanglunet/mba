import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { NotifyTarget, NotifyPayload } from '../../src/types.js';
import { dispatchNotifications } from '../../src/notify/dispatch.js';

const noop = () => {};

const payload: NotifyPayload = {
  event: 'mba.evolution.done',
  brand: 'Test Brand',
  audit_id: 'brand-new',
  previous_audit_id: 'brand-old',
  overall_delta: 3,
  summary: 'Test Brand: overall +3 vs brand-old',
  delta_markdown: '# delta',
};

describe('dispatchNotifications', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllEnvs();
  });

  it('posts to a webhook target and reports success', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const targets: NotifyTarget[] = [{ type: 'webhook', url: 'https://example.com/hook' }];
    const results = await dispatchNotifications(targets, payload, noop);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('https://example.com/hook');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body).brand).toBe('Test Brand');
    expect(results[0].ok).toBe(true);
  });

  it('captures webhook HTTP error into result without throwing', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 500 });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const targets: NotifyTarget[] = [{ type: 'webhook', url: 'https://example.com/hook' }];
    const results = await dispatchNotifications(targets, payload, noop);

    expect(results[0].ok).toBe(false);
    expect(results[0].detail).toContain('500');
  });

  it('captures webhook network failure into result', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('ECONNREFUSED'));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const targets: NotifyTarget[] = [{ type: 'webhook', url: 'https://example.com/hook' }];
    const results = await dispatchNotifications(targets, payload, noop);

    expect(results[0].ok).toBe(false);
    expect(results[0].detail).toContain('ECONNREFUSED');
  });

  it('flags missing webhook url', async () => {
    const targets: NotifyTarget[] = [{ type: 'webhook' }];
    const results = await dispatchNotifications(targets, payload, noop);
    expect(results[0].ok).toBe(false);
    expect(results[0].detail).toBe('missing url');
  });

  it('email returns not-configured when env missing', async () => {
    vi.stubEnv('MBA_RESEND_API_KEY', '');
    vi.stubEnv('MBA_NOTIFY_FROM', '');

    const targets: NotifyTarget[] = [{ type: 'email', address: 'a@b.com' }];
    const results = await dispatchNotifications(targets, payload, noop);

    expect(results[0].ok).toBe(false);
    expect(results[0].detail).toContain('not configured');
  });

  it('email posts to Resend when configured', async () => {
    vi.stubEnv('MBA_RESEND_API_KEY', 're_test');
    vi.stubEnv('MBA_NOTIFY_FROM', 'mba@example.com');
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const targets: NotifyTarget[] = [{ type: 'email', address: 'a@b.com' }];
    const results = await dispatchNotifications(targets, payload, noop);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('https://api.resend.com/emails');
    expect(opts.headers.authorization).toBe('Bearer re_test');
    const body = JSON.parse(opts.body);
    expect(body.to).toBe('a@b.com');
    expect(body.subject).toContain('Test Brand');
    expect(results[0].ok).toBe(true);
  });

  it('mcp-push is served passively (ok, no network)', async () => {
    const fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const targets: NotifyTarget[] = [{ type: 'mcp-push' }];
    const results = await dispatchNotifications(targets, payload, noop);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(results[0].ok).toBe(true);
    expect(results[0].detail).toContain('get_status');
  });

  it('delivers to multiple targets independently', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200 }) // webhook 1 ok
      .mockRejectedValueOnce(new Error('timeout')); // webhook 2 fail
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const targets: NotifyTarget[] = [
      { type: 'webhook', url: 'https://a.com' },
      { type: 'webhook', url: 'https://b.com' },
    ];
    const results = await dispatchNotifications(targets, payload, noop);

    expect(results).toHaveLength(2);
    expect(results[0].ok).toBe(true);
    expect(results[1].ok).toBe(false);
  });
});
