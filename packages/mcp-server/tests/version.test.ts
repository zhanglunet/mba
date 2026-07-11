import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { SERVER_VERSION } from '../src/version.js';

// version.ts is the single source of truth for the server version: server.ts's McpServer
// registration and the report.md footer + report.html meta div (phase-5-merge.ts) all import
// SERVER_VERSION instead of hard-coding '0.1.0' in three places. This guard is what makes that
// DRY safe — bump package.json without bumping version.ts (or vice-versa) and this goes red.
// readFileSync (not a JSON import) is deliberate: package.json is outside tsconfig rootDir and
// resolveJsonModule is off, so an `import pkg from '../package.json'` would break the build.
describe('SERVER_VERSION', () => {
  it('stays in sync with package.json', () => {
    const pkg = JSON.parse(
      readFileSync(new URL('../package.json', import.meta.url), 'utf8'),
    ) as { version: string };
    expect(SERVER_VERSION).toBe(pkg.version);
  });

  it('is a semver-shaped string', () => {
    expect(SERVER_VERSION).toMatch(/^\d+\.\d+\.\d+/);
  });
});
