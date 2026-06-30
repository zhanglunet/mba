import { readFile, writeFile, readdir, mkdir, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { existsSync } from 'node:fs';
import type { AuditState } from '../types.js';
import { atomicWrite } from './atomic.js';

export class FilesystemStore {
  constructor(private readonly storeDir: string) {}

  private auditDir(auditId: string): string {
    return join(this.storeDir, 'audits', auditId);
  }

  private statePath(auditId: string): string {
    return join(this.auditDir(auditId), 'state.json');
  }

  async initAudit(state: AuditState): Promise<void> {
    const dir = this.auditDir(state.audit_id);
    await mkdir(join(dir, '_raw'), { recursive: true });
    await mkdir(join(dir, 'reviews'), { recursive: true });
    await this.writeState(state);
  }

  async readState(auditId: string): Promise<AuditState | null> {
    const path = this.statePath(auditId);
    if (!existsSync(path)) return null;
    const raw = await readFile(path, 'utf-8');
    return JSON.parse(raw) as AuditState;
  }

  async writeState(state: AuditState): Promise<void> {
    await atomicWrite(this.statePath(state.audit_id), JSON.stringify(state, null, 2));
  }

  async writeFile(auditId: string, relativePath: string, content: string): Promise<void> {
    const full = join(this.auditDir(auditId), relativePath);
    await atomicWrite(full, content);
  }

  async readFile(auditId: string, relativePath: string): Promise<string | null> {
    const full = join(this.auditDir(auditId), relativePath);
    if (!existsSync(full)) return null;
    return readFile(full, 'utf-8');
  }

  async listAudits(): Promise<string[]> {
    const auditsDir = join(this.storeDir, 'audits');
    if (!existsSync(auditsDir)) return [];
    const entries = await readdir(auditsDir, { withFileTypes: true });
    return entries.filter(e => e.isDirectory()).map(e => e.name);
  }

  async exists(auditId: string): Promise<boolean> {
    return existsSync(this.statePath(auditId));
  }
}
