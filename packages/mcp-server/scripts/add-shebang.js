#!/usr/bin/env node
// Prepend #!/usr/bin/env node to dist/index.js and make it executable
import { readFileSync, writeFileSync, chmodSync } from 'node:fs';

const entry = new URL('../dist/index.js', import.meta.url).pathname;
const src = readFileSync(entry, 'utf-8');
if (!src.startsWith('#!')) {
  writeFileSync(entry, '#!/usr/bin/env node\n' + src);
}
chmodSync(entry, 0o755);
