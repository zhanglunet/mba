import type { Subscription, CronTriggerConfig } from '../types.js';
import type { SubscriptionStore } from '../store/subscriptions.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { StateMachine } from './state-machine.js';
import type { LLMClient } from '../llm/client.js';
import type { RunnerConfig } from './runner.js';
import { triggerEvolution } from '../tools/trigger-evolution.js';

const TICK_INTERVAL_MS = 60_000; // check every minute

export class CronScheduler {
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private readonly subStore: SubscriptionStore,
    private readonly auditStore: FilesystemStore,
    private readonly sm: StateMachine,
    private readonly runnerConfig: RunnerConfig,
    private readonly client: LLMClient,
    private readonly log: (level: string, msg: string) => void,
  ) {}

  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => {
      this.tick().catch(err => this.log('error', `Scheduler tick error: ${err}`));
    }, TICK_INTERVAL_MS);
    // Don't block process exit
    if (this.timer.unref) this.timer.unref();
    this.log('info', 'CronScheduler started');
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
      this.log('info', 'CronScheduler stopped');
    }
  }

  async tick(): Promise<void> {
    const subs = await this.subStore.list();
    const active = subs.filter(s => s.active);

    for (const sub of active) {
      const cronTriggers = sub.triggers.filter(t => t.type === 'cron');
      for (const trigger of cronTriggers) {
        if (this.isCronDue(sub, trigger.config as CronTriggerConfig)) {
          this.log('info', `[scheduler] Cron trigger due for ${sub.brand} (sub ${sub.id})`);
          await triggerEvolution(
            { brand: sub.brand },
            this.auditStore,
            this.subStore,
            this.sm,
            this.runnerConfig,
            this.client,
            this.log,
          ).catch(err => this.log('error', `[scheduler] Evolution trigger failed for ${sub.brand}: ${err}`));
        }
      }
    }
  }

  private isCronDue(sub: Subscription, config: CronTriggerConfig): boolean {
    const intervalMs = config.interval_days * 24 * 60 * 60 * 1000;
    const lastMs = sub.last_triggered_at
      ? new Date(sub.last_triggered_at).getTime()
      : new Date(sub.created_at).getTime();

    if (Date.now() - lastMs < intervalMs) return false;

    // If run_at is set, only trigger in the correct UTC hour:minute window
    if (config.run_at) {
      const [hh, mm] = config.run_at.split(':').map(Number);
      const now = new Date();
      if (now.getUTCHours() !== hh || now.getUTCMinutes() !== mm) return false;
    }

    return true;
  }
}
