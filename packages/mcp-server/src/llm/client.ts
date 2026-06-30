import Anthropic from '@anthropic-ai/sdk';

const DEFAULT_MODEL = 'claude-sonnet-4-6';
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = [2000, 4000, 8000];

export interface LLMResult {
  content: string;
  input_tokens: number;
  output_tokens: number;
}

export class LLMClient {
  private client: Anthropic;
  readonly model: string;

  constructor(apiKey: string, model = DEFAULT_MODEL) {
    this.client = new Anthropic({ apiKey, maxRetries: 0 });
    this.model = model;
  }

  async complete(
    systemPrompt: string,
    userMessage: string,
    maxTokens = 8192,
  ): Promise<LLMResult> {
    let lastErr: Error | undefined;
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      try {
        const msg = await this.client.messages.create({
          model: this.model,
          max_tokens: maxTokens,
          system: systemPrompt,
          messages: [{ role: 'user', content: userMessage }],
        });

        const content = msg.content
          .filter(b => b.type === 'text')
          .map(b => (b as { type: 'text'; text: string }).text)
          .join('');

        return {
          content,
          input_tokens: msg.usage.input_tokens,
          output_tokens: msg.usage.output_tokens,
        };
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

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
