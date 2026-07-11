import { describe, it, expect } from 'vitest';

// Env-gated LIVE smoke — the one thing offline mocks structurally cannot catch: a real
// Anthropic SDK response-shape drift (usage fields, content-block union). SKIPPED unless BOTH
//   MBA_LIVE_E2E=1  and  ANTHROPIC_API_KEY=<key>
// are set, so it never runs in CI or offline dev. This is the scaffold F5 deferred here (the
// skill⇄MCP score-layer parity is already covered offline in scores.test.ts).
//
//   Run locally:
//     MBA_LIVE_E2E=1 ANTHROPIC_API_KEY=sk-ant-... pnpm --filter mba-mcp-server test smoke.e2e
const LIVE = process.env.MBA_LIVE_E2E === '1' && Boolean(process.env.ANTHROPIC_API_KEY);

describe.skipIf(!LIVE)('live smoke (real Anthropic API)', () => {
  it('LLMClient.complete returns a well-formed completion with token usage', async () => {
    const { LLMClient } = await import('../../src/llm/client.js');
    const client = new LLMClient(process.env.ANTHROPIC_API_KEY!);

    const res = await client.complete(
      'You are a test probe. Reply with exactly one word.',
      'Reply with the single word: PONG',
      16,
    );

    expect(typeof res.content).toBe('string');
    expect(res.content.trim().length).toBeGreaterThan(0);
    expect(res.input_tokens).toBeGreaterThan(0);
    expect(res.output_tokens).toBeGreaterThan(0);
  }, 30_000);
});
