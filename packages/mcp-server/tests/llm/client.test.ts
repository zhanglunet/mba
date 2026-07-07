import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the Anthropic SDK so we can assert exactly what params reach messages.create.
const createMock = vi.fn();
vi.mock('@anthropic-ai/sdk', () => {
  class APIError extends Error {
    status: number;
    constructor(status = 500) {
      super('api error');
      this.status = status;
    }
  }
  const Anthropic = vi.fn().mockImplementation(() => ({ messages: { create: createMock } }));
  (Anthropic as unknown as { APIError: unknown }).APIError = APIError;
  return { default: Anthropic };
});

import { LLMClient, extractSources } from '../../src/llm/client.js';

function textMsg(text: string, extra: unknown[] = [], usage: Record<string, unknown> = {}) {
  return {
    content: [{ type: 'text', text }, ...extra],
    usage: { input_tokens: 10, output_tokens: 20, ...usage },
  };
}

beforeEach(() => {
  createMock.mockReset();
});

describe('LLMClient web search wiring', () => {
  it('does not attach the web_search tool when search is not enabled', async () => {
    createMock.mockResolvedValue(textMsg('plain answer'));
    const client = new LLMClient('sk-test', 'claude-sonnet-4-6', { webSearch: false });

    const res = await client.complete('sys', 'user', 1024, { search: true });

    expect(res.content).toBe('plain answer');
    const params = createMock.mock.calls[0][0];
    expect(params.tools).toBeUndefined();
  });

  it('attaches the web_search tool when enabled and the call opts in', async () => {
    createMock.mockResolvedValue(textMsg('answer'));
    const client = new LLMClient('sk-test', 'claude-sonnet-4-6', { webSearch: true, webSearchMaxUses: 3 });

    await client.complete('sys', 'user', 1024, { search: true });

    const params = createMock.mock.calls[0][0];
    expect(params.tools).toEqual([
      { type: 'web_search_20250305', name: 'web_search', max_uses: 3 },
    ]);
  });

  it('does not search when enabled but the call does not opt in', async () => {
    createMock.mockResolvedValue(textMsg('answer'));
    const client = new LLMClient('sk-test', 'claude-sonnet-4-6', { webSearch: true });

    await client.complete('sys', 'user'); // no { search: true }

    expect(createMock.mock.calls[0][0].tools).toBeUndefined();
  });

  it('folds real sources into content and reports search_uses', async () => {
    const searchBlock = {
      type: 'web_search_tool_result',
      content: [
        { type: 'web_search_result', url: 'https://a.example/x', title: 'A' },
        { type: 'web_search_result', url: 'https://b.example/y', title: 'B' },
      ],
    };
    createMock.mockResolvedValue(
      textMsg('the analysis', [searchBlock], { server_tool_use: { web_search_requests: 2 } }),
    );
    const client = new LLMClient('sk-test', 'claude-sonnet-4-6', { webSearch: true });

    const res = await client.complete('sys', 'user', 1024, { search: true });

    expect(res.sources).toEqual([
      { url: 'https://a.example/x', title: 'A' },
      { url: 'https://b.example/y', title: 'B' },
    ]);
    expect(res.search_uses).toBe(2);
    expect(res.content).toContain('## Sources');
    expect(res.content).toContain('[A](https://a.example/x)');
  });

  it('defaults webSearchMaxUses to 5', async () => {
    createMock.mockResolvedValue(textMsg('x'));
    const client = new LLMClient('sk-test', 'claude-sonnet-4-6', { webSearch: true });
    await client.complete('sys', 'user', 1024, { search: true });
    expect(createMock.mock.calls[0][0].tools[0].max_uses).toBe(5);
  });
});

describe('extractSources', () => {
  it('collects and dedupes urls from search results and text citations', () => {
    const blocks = [
      {
        type: 'web_search_tool_result',
        content: [
          { type: 'web_search_result', url: 'https://one.example', title: 'One' },
          { type: 'web_search_result', url: 'https://one.example', title: 'One dup' }, // dup
        ],
      },
      { type: 'text', text: 'hi', citations: [{ url: 'https://two.example', title: 'Two' }] },
      { type: 'text', text: 'no citations here' },
    ];
    expect(extractSources(blocks)).toEqual([
      { url: 'https://one.example', title: 'One' },
      { url: 'https://two.example', title: 'Two' },
    ]);
  });

  it('returns empty for blocks with no sources', () => {
    expect(extractSources([{ type: 'text', text: 'nothing' }])).toEqual([]);
  });
});
