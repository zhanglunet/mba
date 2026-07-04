import type { UnsubscribeBrandInput, UnsubscribeBrandOutput } from '../types.js';
import type { SubscriptionStore } from '../store/subscriptions.js';

export async function unsubscribeBrand(
  input: UnsubscribeBrandInput,
  store: SubscriptionStore,
): Promise<UnsubscribeBrandOutput> {
  const sub = await store.read(input.subscription_id);
  if (!sub) {
    throw new Error(`SUBSCRIPTION_NOT_FOUND: ${input.subscription_id}`);
  }

  await store.delete(input.subscription_id);

  return {
    unsubscribed: true,
    subscription_id: input.subscription_id,
  };
}
