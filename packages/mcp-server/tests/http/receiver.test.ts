import { describe, it, expect, vi, afterEach } from 'vitest';
import type { AddressInfo } from 'node:net';
import type { Server } from 'node:http';
import { createReceiver, HttpError } from '../../src/http/receiver.js';
import type { TriggerEvolutionInput, TriggerEvolutionOutput } from '../../src/types.js';

const noop = () => {};

function okResult(over: Partial<TriggerEvolutionOutput> = {}): TriggerEvolutionOutput {
  return { audit_id: 'brand-20260101-1200', phase: 'researching', message: 'started', ...over };
}

let server: Server | undefined;

async function start(opts: Partial<Parameters<typeof createReceiver>[0]> = {}): Promise<string> {
  const s = createReceiver({
    handleTrigger: vi.fn().mockResolvedValue(okResult()),
    log: noop,
    ...opts,
  });
  server = s;
  await new Promise<void>(resolve => s.listen(0, '127.0.0.1', resolve));
  const { port } = s.address() as AddressInfo;
  return `http://127.0.0.1:${port}`;
}

afterEach(async () => {
  if (server) await new Promise<void>(r => server!.close(() => r()));
  server = undefined;
});

describe('webhook receiver', () => {
  it('GET /health returns 200', async () => {
    const base = await start();
    const res = await fetch(`${base}/health`);
    expect(res.status).toBe(200);
    expect((await res.json()).ok).toBe(true);
  });

  it('POST /webhooks/trigger with valid body → 202 and parses input', async () => {
    const handleTrigger = vi.fn().mockResolvedValue(okResult());
    const base = await start({ handleTrigger });
    const res = await fetch(`${base}/webhooks/trigger`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ brand: '  Xiaomi  ', event_type: 'product_launch', event_summary: 'YU7', force: true, junk: 1 }),
    });
    expect(res.status).toBe(202);
    expect((await res.json()).audit_id).toBe('brand-20260101-1200');
    const input = handleTrigger.mock.calls[0][0] as TriggerEvolutionInput;
    expect(input.brand).toBe('Xiaomi'); // trimmed
    expect(input.event_type).toBe('product_launch');
    expect(input.force).toBe(true);
  });

  it('skipped result (cadence guard) → 200', async () => {
    const base = await start({
      handleTrigger: vi.fn().mockResolvedValue(okResult({ skipped: true, audit_id: '', message: 'cadence' })),
    });
    const res = await fetch(`${base}/webhooks/trigger`, {
      method: 'POST',
      body: JSON.stringify({ brand: 'Xiaomi' }),
    });
    expect(res.status).toBe(200);
    expect((await res.json()).skipped).toBe(true);
  });

  it('missing brand → 400', async () => {
    const base = await start();
    const res = await fetch(`${base}/webhooks/trigger`, { method: 'POST', body: JSON.stringify({ event_type: 'x' }) });
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBe('MISSING_BRAND');
  });

  it('invalid JSON → 400', async () => {
    const base = await start();
    const res = await fetch(`${base}/webhooks/trigger`, { method: 'POST', body: '{not json' });
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBe('INVALID_JSON');
  });

  it('GET on trigger path → 405', async () => {
    const base = await start();
    const res = await fetch(`${base}/webhooks/trigger`);
    expect(res.status).toBe(405);
  });

  it('unknown path → 404', async () => {
    const base = await start();
    const res = await fetch(`${base}/nope`);
    expect(res.status).toBe(404);
  });

  it('trailing slash is normalized', async () => {
    const base = await start();
    const res = await fetch(`${base}/webhooks/trigger/`, { method: 'POST', body: JSON.stringify({ brand: 'X' }) });
    expect(res.status).toBe(202);
  });

  describe('auth', () => {
    it('rejects missing token when secret set → 401', async () => {
      const base = await start({ secret: 's3cr3t' });
      const res = await fetch(`${base}/webhooks/trigger`, { method: 'POST', body: JSON.stringify({ brand: 'X' }) });
      expect(res.status).toBe(401);
    });

    it('rejects wrong token → 401', async () => {
      const base = await start({ secret: 's3cr3t' });
      const res = await fetch(`${base}/webhooks/trigger`, {
        method: 'POST',
        headers: { authorization: 'Bearer nope' },
        body: JSON.stringify({ brand: 'X' }),
      });
      expect(res.status).toBe(401);
    });

    it('accepts correct token → 202', async () => {
      const base = await start({ secret: 's3cr3t' });
      const res = await fetch(`${base}/webhooks/trigger`, {
        method: 'POST',
        headers: { authorization: 'Bearer s3cr3t' },
        body: JSON.stringify({ brand: 'X' }),
      });
      expect(res.status).toBe(202);
    });
  });

  it('oversized body → 413', async () => {
    const base = await start({ maxBodyBytes: 64 });
    const res = await fetch(`${base}/webhooks/trigger`, {
      method: 'POST',
      body: JSON.stringify({ brand: 'X', event_summary: 'y'.repeat(500) }),
    });
    expect(res.status).toBe(413);
  });

  it('handler HttpError propagates its status (503 no API key)', async () => {
    const base = await start({
      handleTrigger: vi.fn().mockRejectedValue(new HttpError(503, 'MISSING_API_KEY', 'no key')),
    });
    const res = await fetch(`${base}/webhooks/trigger`, { method: 'POST', body: JSON.stringify({ brand: 'X' }) });
    expect(res.status).toBe(503);
    expect((await res.json()).error).toBe('MISSING_API_KEY');
  });

  it('unexpected handler error → 500', async () => {
    const base = await start({ handleTrigger: vi.fn().mockRejectedValue(new Error('boom')) });
    const res = await fetch(`${base}/webhooks/trigger`, { method: 'POST', body: JSON.stringify({ brand: 'X' }) });
    expect(res.status).toBe(500);
  });

  describe('GET /status', () => {
    it('returns status when found', async () => {
      const base = await start({
        handleStatus: vi.fn().mockResolvedValue({ audit_id: 'a1', brand: 'X', phase: 'done', progress_pct: 100 } as never),
      });
      const res = await fetch(`${base}/status?audit_id=a1`);
      expect(res.status).toBe(200);
      expect((await res.json()).phase).toBe('done');
    });

    it('404 when not found', async () => {
      const base = await start({ handleStatus: vi.fn().mockResolvedValue(null) });
      const res = await fetch(`${base}/status?audit_id=missing`);
      expect(res.status).toBe(404);
    });

    it('400 when audit_id missing', async () => {
      const base = await start({ handleStatus: vi.fn().mockResolvedValue(null) });
      const res = await fetch(`${base}/status`);
      expect(res.status).toBe(400);
    });

    it('404 when status endpoint not configured', async () => {
      const base = await start(); // no handleStatus
      const res = await fetch(`${base}/status?audit_id=a1`);
      expect(res.status).toBe(404);
    });
  });
});
