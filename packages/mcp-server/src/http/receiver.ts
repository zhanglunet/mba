import { createServer, type Server, type IncomingMessage, type ServerResponse } from 'node:http';
import { timingSafeEqual } from 'node:crypto';
import type { TriggerEvolutionInput, TriggerEvolutionOutput, GetStatusOutput } from '../types.js';

/**
 * Error a handler can throw to control the HTTP status code the receiver
 * responds with. Anything else becomes a 500.
 */
export class HttpError extends Error {
  constructor(
    readonly statusCode: number,
    readonly code: string,
    message?: string,
  ) {
    super(message ?? code);
  }
}

export interface ReceiverOptions {
  /** Start (or skip) an EVOLUTION audit for the posted event. */
  handleTrigger: (input: TriggerEvolutionInput) => Promise<TriggerEvolutionOutput>;
  /** Optional status lookup for GET /status?audit_id=… */
  handleStatus?: (auditId: string) => Promise<GetStatusOutput | null>;
  /** If set, POSTs must carry `Authorization: Bearer <secret>`. */
  secret?: string;
  /** Max request body size in bytes (default 64 KiB). */
  maxBodyBytes?: number;
  log: (level: string, msg: string) => void;
}

const DEFAULT_MAX_BODY = 64 * 1024;

function send(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json',
    'content-length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

/** Constant-time secret comparison that tolerates length differences. */
function secretMatches(provided: string, expected: string): boolean {
  const a = Buffer.from(provided);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

function readBody(req: IncomingMessage, maxBytes: number): Promise<string> {
  return new Promise((resolve, reject) => {
    let size = 0;
    let aborted = false;
    const chunks: Buffer[] = [];
    req.on('data', (chunk: Buffer) => {
      if (aborted) return;
      size += chunk.length;
      if (size > maxBytes) {
        // Reject so the handler can flush a 413, but leave the socket intact
        // (destroying it here would abort the response the client is waiting for).
        aborted = true;
        reject(new HttpError(413, 'PAYLOAD_TOO_LARGE', `body exceeds ${maxBytes} bytes`));
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (!aborted) resolve(Buffer.concat(chunks).toString('utf-8'));
    });
    req.on('error', reject);
  });
}

/**
 * Build the MBA webhook receiver — a small HTTP server that turns an inbound
 * event POST into an EVOLUTION re-audit. Pure and dependency-injected so it can
 * be unit-tested without running real audits.
 *
 * Routes:
 *   GET  /health              → { ok: true }
 *   POST /webhooks/trigger     → { audit_id, phase, … } (202) or skip (200)
 *   GET  /status?audit_id=…    → status (200) / not found (404)  [if handleStatus]
 */
export function createReceiver(opts: ReceiverOptions): Server {
  const maxBytes = opts.maxBodyBytes ?? DEFAULT_MAX_BODY;

  return createServer((req: IncomingMessage, res: ServerResponse) => {
    void handle(req, res).catch(err => {
      if (err instanceof HttpError) {
        send(res, err.statusCode, { error: err.code, message: err.message });
      } else {
        opts.log('error', `[receiver] unhandled: ${err instanceof Error ? err.message : err}`);
        send(res, 500, { error: 'INTERNAL_ERROR' });
      }
    });
  });

  async function handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const path = url.pathname.replace(/\/+$/, '') || '/';
    const method = req.method ?? 'GET';

    // ── GET /health ──────────────────────────────────────────────────────
    if (path === '/health') {
      if (method !== 'GET') throw new HttpError(405, 'METHOD_NOT_ALLOWED');
      send(res, 200, { ok: true, service: 'mba-webhook-receiver' });
      return;
    }

    // ── GET /status ──────────────────────────────────────────────────────
    if (path === '/status') {
      if (!opts.handleStatus) throw new HttpError(404, 'NOT_FOUND');
      if (method !== 'GET') throw new HttpError(405, 'METHOD_NOT_ALLOWED');
      const auditId = url.searchParams.get('audit_id');
      if (!auditId) throw new HttpError(400, 'MISSING_AUDIT_ID', 'audit_id query param required');
      const status = await opts.handleStatus(auditId);
      if (!status) throw new HttpError(404, 'AUDIT_NOT_FOUND', auditId);
      send(res, 200, status);
      return;
    }

    // ── POST /webhooks/trigger ───────────────────────────────────────────
    if (path === '/webhooks/trigger') {
      if (method !== 'POST') throw new HttpError(405, 'METHOD_NOT_ALLOWED');

      // Auth (optional shared secret)
      if (opts.secret) {
        const auth = req.headers['authorization'];
        const token = typeof auth === 'string' && auth.startsWith('Bearer ')
          ? auth.slice(7)
          : '';
        if (!token || !secretMatches(token, opts.secret)) {
          throw new HttpError(401, 'UNAUTHORIZED', 'valid Bearer token required');
        }
      }

      const raw = await readBody(req, maxBytes);
      let body: Record<string, unknown>;
      try {
        body = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
      } catch {
        throw new HttpError(400, 'INVALID_JSON', 'request body is not valid JSON');
      }

      const brand = body['brand'];
      if (typeof brand !== 'string' || brand.trim() === '') {
        throw new HttpError(400, 'MISSING_BRAND', 'field "brand" (non-empty string) is required');
      }

      const input: TriggerEvolutionInput = {
        brand: brand.trim(),
        event_type: typeof body['event_type'] === 'string' ? (body['event_type'] as string) : undefined,
        event_summary: typeof body['event_summary'] === 'string' ? (body['event_summary'] as string) : undefined,
        source_url: typeof body['source_url'] === 'string' ? (body['source_url'] as string) : undefined,
        force: body['force'] === true,
      };

      opts.log('info', `[receiver] trigger: ${input.brand}${input.event_type ? ` (${input.event_type})` : ''}`);
      const result = await opts.handleTrigger(input);

      // 200 when cadence-guarded/skipped, 202 when an audit actually started.
      send(res, result.skipped ? 200 : 202, result);
      return;
    }

    throw new HttpError(404, 'NOT_FOUND');
  }
}
