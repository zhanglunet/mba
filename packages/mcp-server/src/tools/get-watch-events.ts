import type { GetWatchEventsInput, GetWatchEventsOutput } from '../types.js';
import { WatchStore } from '../watch/store.js';
import { evaluateTrigger } from '../watch/trigger.js';

/**
 * get_watch_events — 读某品牌的舆情事件流(watch/<slug>/events.yaml),
 * 附带触发规则运行时评估(30 天滚动窗)。只读,不改任何文件。
 */
export async function getWatchEvents(
  input: GetWatchEventsInput,
  watchStore: WatchStore,
): Promise<GetWatchEventsOutput> {
  const slug = input.brand.trim().toLowerCase();
  const all = await watchStore.readEvents(slug);

  let events = all;
  if (input.since) events = events.filter(e => e.date >= input.since!);
  if (input.dim) events = events.filter(e => e.dim === input.dim);
  if (input.severity) events = events.filter(e => e.severity === input.severity);
  if (input.unconsumed_only) events = events.filter(e => !e.consumed_by);

  // 触发评估始终基于全量事件(不受 since/dim 过滤影响)——评估的是品牌,不是查询子集。
  const trigger = evaluateTrigger(all);

  return {
    brand: slug,
    count: events.length,
    events: [...events].sort((a, b) => b.date.localeCompare(a.date)),
    trigger,
  };
}
