import type { ListSubscriptionsOutput } from '../types.js';
import type { SubscriptionStore } from '../store/subscriptions.js';

export async function listSubscriptions(store: SubscriptionStore): Promise<ListSubscriptionsOutput> {
  const all = await store.list();
  return {
    subscriptions: all.map(s => ({
      subscription_id: s.id,
      brand: s.brand,
      panel: s.panel,
      triggers: s.triggers,
      active: s.active,
      last_triggered_at: s.last_triggered_at,
      last_audit_id: s.last_audit_id,
    })),
  };
}
