import { randomUUID } from 'node:crypto';
import type {
  SubscribeBrandInput,
  SubscribeBrandOutput,
  Subscription,
  Trigger,
  NotifyTarget,
} from '../types.js';
import type { SubscriptionStore } from '../store/subscriptions.js';
import { slugify } from '../orchestrator/state-machine.js';

export async function subscribeBrand(
  input: SubscribeBrandInput,
  store: SubscriptionStore,
): Promise<SubscribeBrandOutput> {
  const brand_slug = slugify(input.brand);
  const panel = input.panel ?? 'default';

  // Build triggers — default to daily cron if none provided
  const triggers: Trigger[] = (input.triggers ?? [{ type: 'cron', config: { interval_days: 7 } }]).map(t => ({
    type: t.type as Trigger['type'],
    config: t.config ?? {},
  }));

  const notify: NotifyTarget[] = (input.notify ?? []).map(n => ({
    type: n.type as NotifyTarget['type'],
    url: n.url,
    address: n.address,
  }));

  const now = new Date().toISOString();
  const monthStart = new Date();
  monthStart.setUTCDate(1);
  monthStart.setUTCHours(0, 0, 0, 0);

  const sub: Subscription = {
    id: randomUUID(),
    brand: input.brand,
    brand_slug,
    panel,
    triggers,
    notify,
    cadence: {
      min_interval_days: input.min_interval_days ?? 7,
      max_per_month: input.max_per_month ?? 4,
    },
    created_at: now,
    trigger_count_this_month: 0,
    month_reset_at: monthStart.toISOString(),
    active: true,
  };

  await store.write(sub);

  return {
    subscription_id: sub.id,
    brand: sub.brand,
    panel: sub.panel,
    triggers: sub.triggers,
    message: `Subscribed to ${input.brand}. Triggers: ${triggers.map(t => t.type).join(', ')}. Poll get_status after trigger_evolution fires.`,
  };
}
