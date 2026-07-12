import type {
  RecordWatchEventInput,
  RecordWatchEventOutput,
  WatchEvent,
  NotifyResult,
  NotifyPayload,
} from '../types.js';
import { WatchStore } from '../watch/store.js';
import { evaluateTrigger } from '../watch/trigger.js';
import { SubscriptionStore } from '../store/subscriptions.js';
import { dispatchNotifications } from '../notify/dispatch.js';

/**
 * record_watch_event — 录入一条舆情事件并评估触发规则(docs/15 §5.3 / §6.3)。
 *
 * 反捏造门槛与 validate_watch.py 同一套:事实字段(date/quote/url/fetched_at)
 * 必须齐且合规,quote 逐字 ≤100 字;判断字段恒标 model-judged;consumed_by 拒收
 * (只在审计消费时标记)。录入后若 P0 事件或触发规则命中 → 经既有 subscribe_brand
 * 订阅链路 dispatchNotifications 下发「建议重审」(复用管道,不新造轮子)。
 *
 * 边界:本工具**只录信号、只发建议,永不改分**——分数只能来自评委重审。
 */
export async function recordWatchEvent(
  input: RecordWatchEventInput,
  watchStore: WatchStore,
  subStore: SubscriptionStore,
  log: (level: string, msg: string) => void,
): Promise<RecordWatchEventOutput> {
  const slug = input.brand.trim().toLowerCase();
  const matrix = await watchStore.readMatrix();

  const draft = { ...input.event, direction_by: 'model-judged' as const };
  const errs = watchStore.validateNewEvent(slug, draft, matrix);
  if (errs.length > 0) {
    throw new Error(`WATCH_EVENT_INVALID: ${errs.join('; ')}`);
  }

  const existing = await watchStore.readEvents(slug);
  const id = watchStore.nextEventId(existing, slug, draft.date);
  const event: WatchEvent = { ...draft, id };
  await watchStore.appendEvent(slug, event);
  log('info', `[watch] recorded ${id} (${event.severity} ${event.dim}) for ${slug}`);

  const trigger = evaluateTrigger([...existing, event]);

  // P0 即时告警;或触发规则命中 → 建议重审。均经既有订阅链路下发。
  let notified: NotifyResult[] = [];
  const isP0 = event.severity === 'P0';
  if (isP0 || trigger.hit) {
    const subs = await subStore.findByBrand(slug);
    const targets = subs.flatMap(s => s.notify);
    if (targets.length > 0) {
      const payload: NotifyPayload = {
        event: 'watch_alert',
        brand: slug,
        audit_id: id, // watch 告警无 audit,填事件 id 作追溯锚点
        summary: isP0
          ? `P0 事件:${event.title}(${event.url})— 建议立即 EVOLUTION 重审`
          : `触发规则命中(${trigger.rules_hit.join(', ')})— 建议 EVOLUTION 重审`,
      };
      notified = await dispatchNotifications(targets, payload, log);
    }
  }

  return {
    recorded: true,
    id,
    brand: slug,
    trigger,
    notified,
    message: trigger.hit
      ? `事件已录入。${trigger.recommendation}(通知 ${notified.length} 个目标)`
      : 'Event recorded. 未命中触发规则——只入库,不打扰。',
  };
}
