#!/usr/bin/env node
// Prepend #!/usr/bin/env node to the CLI entry points and make them executable
import { readFileSync, writeFileSync, chmodSync } from 'node:fs';

for (const rel of ['../dist/index.js', '../dist/receiver-main.js']) {
  const entry = new URL(rel, import.meta.url).pathname;
  const src = readFileSync(entry, 'utf-8');
  if (!src.startsWith('#!')) {
    writeFileSync(entry, '#!/usr/bin/env node\n' + src);
  }
  chmodSync(entry, 0o755);
}
