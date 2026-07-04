import { readFile, writeFile, readdir, mkdir, unlink } from 'node:fs/promises';
import { join } from 'node:path';
import { existsSync } from 'node:fs';
import type { Subscription } from '../types.js';
import { atomicWrite } from './atomic.js';

export class SubscriptionStore {
  private readonly subsDir: string;

  constructor(storeDir: string) {
    this.subsDir = join(storeDir, 'subscriptions');
  }

  private subPath(id: string): string {
    return join(this.subsDir, `${id}.json`);
  }

  async write(sub: Subscription): Promise<void> {
    await mkdir(this.subsDir, { recursive: true });
    await atomicWrite(this.subPath(sub.id), JSON.stringify(sub, null, 2));
  }

  async read(id: string): Promise<Subscription | null> {
    const path = this.subPath(id);
    if (!existsSync(path)) return null;
    const raw = await readFile(path, 'utf-8');
    return JSON.parse(raw) as Subscription;
  }

  async list(): Promise<Subscription[]> {
    if (!existsSync(this.subsDir)) return [];
    const entries = await readdir(this.subsDir);
    const subs: Subscription[] = [];
    for (const entry of entries) {
      if (!entry.endsWith('.json')) continue;
      const raw = await readFile(join(this.subsDir, entry), 'utf-8');
      subs.push(JSON.parse(raw) as Subscription);
    }
    return subs.sort((a, b) => a.created_at.localeCompare(b.created_at));
  }

  async delete(id: string): Promise<boolean> {
    const path = this.subPath(id);
    if (!existsSync(path)) return false;
    await unlink(path);
    return true;
  }

  async findByBrand(brandSlug: string): Promise<Subscription[]> {
    const all = await this.list();
    return all.filter(s => s.brand_slug === brandSlug && s.active);
  }
}
