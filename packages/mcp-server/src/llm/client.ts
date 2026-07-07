import Anthropic from '@anthropic-ai/sdk';

const DEFAULT_MODEL = 'claude-sonnet-4-6';
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = [2000, 4000, 8000];

// Anthropic's server-side web search tool. The search runs on Anthropic's
// infrastructure (reached via api.anthropic.com), so enabling it does NOT
// require the sandbox to have any outbound network access of its own.
const WEB_SEARCH_TOOL_TYPE = 'web_search_20250305';

export interface WebSource {
  url: string;
  title?: string;
}

export interface LLMResult {
  content: string;
  input_tokens: number;
  output_tokens: number;
  /** Real source URLs returned by web search (when enabled), for anti-fabrication. */
  sources?: WebSource[];
  /** How many web searches the model actually performed on this request. */
  search_uses?: number;
}

export interface LLMClientOptions {
  /** Enable Anthropic's server-side web_search tool for `complete({ search: true })`.
   *  Defaults to the `MBA_WEB_SEARCH` env var (`1`/`true` → on). */
  webSearch?: boolean;
  /** Max searches per request (Anthropic bills per search). Defaults to
   *  `MBA_WEB_SEARCH_MAX_USES` or 5. */
  webSearchMaxUses?: number;
}

export interface CompleteOptions {
  /** Request live web search for this call. No-op unless the client has web
   *  search enabled. Only the research phases opt in — judging / synthesis /
   *  merge never search. */
  search?: boolean;
}

function envFlag(name: string): boolean {
  const v = process.env[name];
  return v === '1' || v === 'true';
}

export class LLMClient {
  private client: Anthropic;
  readonly model: string;
  readonly webSearchEnabled: boolean;
  readonly webSearchMaxUses: number;

  constructor(apiKey: string, model = DEFAULT_MODEL, opts: LLMClientOptions = {}) {
    this.client = new Anthropic({ apiKey, maxRetries: 0 });
    this.model = model;
    this.webSearchEnabled = opts.webSearch ?? envFlag('MBA_WEB_SEARCH');
    this.webSearchMaxUses =
      opts.webSearchMaxUses ?? Number(process.env['MBA_WEB_SEARCH_MAX_USES'] ?? 5);
  }

  async complete(
    systemPrompt: string,
    userMessage: string,
    maxTokens = 8192,
    options: CompleteOptions = {},
  ): Promise<LLMResult> {
    const useSearch = Boolean(options.search) && this.webSearchEnabled;

    let lastErr: Error | undefined;
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      try {
        const params: Anthropic.MessageCreateParamsNonStreaming = {
          model: this.model,
          max_tokens: maxTokens,
          system: systemPrompt,
          messages: [{ role: 'user', content: userMessage }],
        };
        if (useSearch) {
          // Cast: the web_search tool shape isn't in this SDK version's tool union.
          (params as { tools?: unknown }).tools = [
            { type: WEB_SEARCH_TOOL_TYPE, name: 'web_search', max_uses: this.webSearchMaxUses },
          ];
        }

        const msg = await this.client.messages.create(params);

        const content = msg.content
          .filter(b => b.type === 'text')
          .map(b => (b as { type: 'text'; text: string }).text)
          .join('');

        const result: LLMResult = {
          content,
          input_tokens: msg.usage.input_tokens,
          output_tokens: msg.usage.output_tokens,
        };

        if (useSearch) {
          const sources = extractSources(msg.content);
          const searchUses = (msg.usage as { server_tool_use?: { web_search_requests?: number } })
            .server_tool_use?.web_search_requests;
          if (sources.length > 0) {
            result.sources = sources;
            result.content = `${content}\n\n## Sources\n${sources
              .map(s => `- [${s.title ?? s.url}](${s.url})`)
              .join('\n')}`;
          }
          if (typeof searchUses === 'number') result.search_uses = searchUses;
        }

        return result;
      } catch (err) {
        const isRetryable =
          err instanceof Anthropic.APIError &&
          (err.status === 429 || (err.status >= 500 && err.status < 600));

        if (isRetryable && attempt < MAX_RETRIES - 1) {
          const delay = RETRY_DELAY_MS[attempt] ?? 8000;
          await sleep(delay);
          lastErr = err as Error;
          continue;
        }
        throw err;
      }
    }
    throw lastErr ?? new Error('LLM request failed after retries');
  }
}

// Pull real source URLs out of the response: primarily the web_search_tool_result
// blocks the tool emits, with text-citation URLs as a fallback. Deduped by URL.
export function extractSources(blocks: unknown[]): WebSource[] {
  const byUrl = new Map<string, WebSource>();
  for (const raw of blocks) {
    const b = raw as { type?: string; content?: unknown; citations?: unknown };
    if (b.type === 'web_search_tool_result' && Array.isArray(b.content)) {
      for (const r of b.content as Array<{ type?: string; url?: string; title?: string }>) {
        if (r?.type === 'web_search_result' && r.url && !byUrl.has(r.url)) {
          byUrl.set(r.url, { url: r.url, title: r.title });
        }
      }
    }
    if (b.type === 'text' && Array.isArray(b.citations)) {
      for (const c of b.citations as Array<{ url?: string; title?: string }>) {
        if (c?.url && !byUrl.has(c.url)) byUrl.set(c.url, { url: c.url, title: c.title });
      }
    }
  }
  return [...byUrl.values()];
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
