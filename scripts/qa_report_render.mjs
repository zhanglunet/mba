#!/usr/bin/env node
/**
 * qa_report_render.mjs — headless render QA for published report HTML.
 *
 * Renders each published report in a real browser and catches the failure
 * modes a static validator can't see:
 *   - Chart.js infinite-growth (canvas keeps expanding, ballooning the page).
 *     Root cause: responsive + maintainAspectRatio:false on a canvas whose
 *     container has no fixed height. This is what broke kimichat/qianxin.
 *   - Collapsed / zero-height canvases (chart didn't size).
 *   - Unrendered Mermaid diagrams (no <svg> produced -> syntax error, etc.).
 *   - Any uncaught JS / console error on the page.
 *
 * Usage:
 *   node scripts/qa_report_render.mjs                 # all published reports
 *   node scripts/qa_report_render.mjs kimichat dji    # only these slugs
 *   node scripts/qa_report_render.mjs --offline-libs <dir>
 *
 * By default the page loads Chart.js / Mermaid from their CDNs, so run it
 * with network access. In an air-gapped environment pass --offline-libs <dir>,
 * where <dir> contains:
 *   chart.umd.min.js          (from `npm pack chart.js`,  dist/chart.umd.js)
 *   mermaid/                  (from `npm pack mermaid@11`, the whole dist/)
 *
 * Exit codes: 0 = all pass · 1 = a report FAILed · 2 = libraries never loaded
 * (need network or --offline-libs) · 3 = setup error (Playwright missing).
 *
 * Playwright is not a repo dependency; install on demand:
 *   npm i -D playwright && npx playwright install chromium
 */
import { createRequire } from 'node:module';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..');
const REPORTS_DIR = join(REPO_ROOT, 'published', 'reports');

// ── resolve Playwright (repo has no dep on it) ───────────────────────────────
const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  try {
    // Fall back to a global install (e.g. /opt/node22/lib/node_modules).
    const globalRoot = require('node:child_process')
      .execSync('npm root -g', { encoding: 'utf8' })
      .trim();
    ({ chromium } = require(join(globalRoot, 'playwright')));
  } catch {
    console.error(
      'Playwright not found. Install it:\n' +
        '  npm i -D playwright && npx playwright install chromium',
    );
    process.exit(3);
  }
}

// ── args ─────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
let offlineLibs = null;
const slugs = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--offline-libs') offlineLibs = args[++i];
  else slugs.push(args[i]);
}

function listReports() {
  if (!existsSync(REPORTS_DIR)) return [];
  return readdirSync(REPORTS_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory() && existsSync(join(REPORTS_DIR, e.name, 'report.html')))
    .map((e) => e.name)
    .sort();
}

const targets = (slugs.length ? slugs : listReports()).filter((s) =>
  existsSync(join(REPORTS_DIR, s, 'report.html')),
);
if (!targets.length) {
  console.error('No report.html files found under published/reports/.');
  process.exit(3);
}

// ── optional offline library serving ─────────────────────────────────────────
let chartBody = null;
let mermaidDir = null;
if (offlineLibs) {
  const cp = join(offlineLibs, 'chart.umd.min.js');
  if (existsSync(cp)) chartBody = readFileSync(cp, 'utf8');
  const md = join(offlineLibs, 'mermaid');
  if (existsSync(md)) mermaidDir = md;
}

async function installOfflineRoutes(page) {
  await page.route('**/cdn.jsdelivr.net/**', (route) => {
    const url = route.request().url();
    const mm = url.match(/\/npm\/mermaid@\d+\/dist\/(.+)$/);
    if (mm && mermaidDir) {
      try {
        return route.fulfill({
          status: 200,
          contentType: 'application/javascript',
          body: readFileSync(join(mermaidDir, mm[1]), 'utf8'),
        });
      } catch {
        return route.fulfill({ status: 404, body: 'not vendored' });
      }
    }
    if (/chart\.js|chart\.umd/.test(url) && chartBody) {
      return route.fulfill({ status: 200, contentType: 'application/javascript', body: chartBody });
    }
    return route.continue();
  });
}

// ── per-report render + checks ───────────────────────────────────────────────
const GROW_RATIO = 1.3;
const GROW_ABS = 200;
const T1 = 1500;
const T2 = 6000;

async function checkReport(browser, slug) {
  const html = readFileSync(join(REPORTS_DIR, slug, 'report.html'), 'utf8');
  const usesChart = /chart\.js|chart\.umd|new Chart\(/.test(html);
  const usesMermaid = /class="mermaid"|mermaid\.initialize/.test(html);

  const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push('PAGEERR: ' + e.message.slice(0, 140)));
  page.on('console', (m) => {
    if (m.type() === 'error' && !/Failed to load resource/.test(m.text()))
      errors.push('CONSOLE: ' + m.text().slice(0, 140));
  });
  if (offlineLibs) await installOfflineRoutes(page);

  const url = pathToFileURL(join(REPORTS_DIR, slug, 'report.html')).href;
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });
  } catch (e) {
    errors.push('GOTO: ' + e.message.slice(0, 100));
  }

  const snap = () =>
    page.evaluate(() => ({
      canvases: [...document.querySelectorAll('canvas')].map((c) => ({
        id: c.id || '(noid)',
        h: c.clientHeight,
      })),
      mermaids: [...document.querySelectorAll('.mermaid')].map((n) => ({
        svg: !!n.querySelector('svg'),
      })),
      bodyH: document.body.scrollHeight,
      chartDefined: typeof window.Chart !== 'undefined',
      chartCount: (window.Chart && window.Chart.instances && Object.keys(window.Chart.instances).length) || 0,
    }));

  await page.waitForTimeout(T1);
  const a = await snap();
  await page.waitForTimeout(T2 - T1);
  const b = await snap();
  await page.close();

  // library-load check: if a page uses a lib but it never ran, the result is
  // inconclusive (offline / CDN blocked), not a real failure.
  const chartLoaded = !usesChart || a.chartDefined || a.canvases.some((c) => c.h > 0);
  const mermaidLoaded = !usesMermaid || b.mermaids.some((m) => m.svg);
  if ((usesChart && !a.chartDefined) || (usesMermaid && !mermaidLoaded && !offlineLibs)) {
    return { slug, state: 'INCONCLUSIVE', detail: 'library did not load (network? use --offline-libs)' };
  }

  const grown = a.canvases.map((c, i) => {
    const later = b.canvases[i] ? b.canvases[i].h : 0;
    return { id: c.id, h1: c.h, h2: later, grew: later > c.h * GROW_RATIO && later - c.h > GROW_ABS };
  });
  const growth = grown.filter((g) => g.grew);
  const zero = b.canvases.filter((c) => c.h < 20);
  const badMermaid = usesMermaid ? b.mermaids.filter((m) => !m.svg) : [];
  const bodyGrew = b.bodyH > a.bodyH * 1.2;

  const problems = [];
  if (growth.length) problems.push('canvas growth: ' + growth.map((g) => `${g.id} ${g.h1}->${g.h2}px`).join(', '));
  if (bodyGrew) problems.push(`page height grew ${a.bodyH}->${b.bodyH}px`);
  if (zero.length) problems.push('zero-height canvas: ' + zero.map((c) => c.id).join(', '));
  if (badMermaid.length) problems.push(`${badMermaid.length} Mermaid diagram(s) produced no SVG`);
  if (errors.length) problems.push('JS errors: ' + errors.join(' | '));

  return {
    slug,
    state: problems.length ? 'FAIL' : 'OK',
    detail: problems.join('; '),
    meta: `canvas=${b.canvases.length}${usesMermaid ? ` mermaid=${b.mermaids.length}` : ''} bodyH=${b.bodyH}`,
  };
}

// ── run ──────────────────────────────────────────────────────────────────────
const browser = await chromium.launch();
let failed = 0;
let inconclusive = 0;
console.log(`QA rendering ${targets.length} report(s)${offlineLibs ? ' [offline libs]' : ''}\n`);
for (const slug of targets) {
  const r = await checkReport(browser, slug);
  const tag = r.state === 'OK' ? 'ok  ' : r.state === 'FAIL' ? 'FAIL' : 'skip';
  console.log(`${tag}  ${slug.padEnd(16)} ${r.meta || ''}`);
  if (r.detail) console.log(`      ${r.detail}`);
  if (r.state === 'FAIL') failed++;
  if (r.state === 'INCONCLUSIVE') inconclusive++;
}
await browser.close();

console.log(`\n${targets.length - failed - inconclusive}/${targets.length} passed` +
  (inconclusive ? ` · ${inconclusive} inconclusive` : '') +
  (failed ? ` · ${failed} FAILED` : ''));
if (failed) process.exit(1);
if (inconclusive) process.exit(2);
process.exit(0);
