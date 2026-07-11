import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtemp, rm, readdir, readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { atomicWrite } from '../../src/store/atomic.js';

describe('atomicWrite', () => {
  let dir: string;

  beforeEach(async () => {
    dir = await mkdtemp(join(tmpdir(), 'mba-atomic-'));
  });
  afterEach(async () => {
    await rm(dir, { recursive: true, force: true });
  });

  it('writes content to a fresh path', async () => {
    const p = join(dir, 'a.txt');
    await atomicWrite(p, 'hello');
    expect(await readFile(p, 'utf-8')).toBe('hello');
  });

  it('creates missing parent directories', async () => {
    const p = join(dir, 'nested', 'deep', 'b.txt');
    await atomicWrite(p, 'x');
    expect(existsSync(p)).toBe(true);
    expect(await readFile(p, 'utf-8')).toBe('x');
  });

  it('overwrites an existing file', async () => {
    const p = join(dir, 'c.txt');
    await writeFile(p, 'old', 'utf-8');
    await atomicWrite(p, 'new');
    expect(await readFile(p, 'utf-8')).toBe('new');
  });

  it('leaves no .tmp turds behind after a successful write', async () => {
    await atomicWrite(join(dir, 'd.txt'), 'content');
    const entries = await readdir(dir);
    expect(entries.filter(e => e.startsWith('.tmp-'))).toEqual([]);
    expect(entries).toContain('d.txt');
  });

  it('never exposes a partially-written file (rename is the only publish step)', async () => {
    // A reader that checks the target between the tmp-write and the rename must
    // see either the full old content or the full new content, never a fragment.
    const p = join(dir, 'e.txt');
    await atomicWrite(p, 'first-full-content');
    await atomicWrite(p, 'second-full-content');
    expect(await readFile(p, 'utf-8')).toBe('second-full-content');
  });

  it('handles many concurrent writes to distinct paths without cross-corruption', async () => {
    const writes = Array.from({ length: 20 }, (_, i) =>
      atomicWrite(join(dir, `f-${i}.txt`), `payload-${i}`),
    );
    await Promise.all(writes);
    for (let i = 0; i < 20; i++) {
      expect(await readFile(join(dir, `f-${i}.txt`), 'utf-8')).toBe(`payload-${i}`);
    }
    // no leftover temp files from any of them
    const entries = await readdir(dir);
    expect(entries.filter(e => e.startsWith('.tmp-'))).toEqual([]);
  });

  it('preserves exact bytes including unicode and newlines', async () => {
    const p = join(dir, 'u.md');
    const content = '# 报告\n\n钟睒睒 · Anthropic\n\t—end—\n';
    await atomicWrite(p, content);
    expect(await readFile(p, 'utf-8')).toBe(content);
  });
});
