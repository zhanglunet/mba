#!/usr/bin/env node
/**
 * zhihu_fetch.mjs — 用 Playwright + 持久登录态(storageState)抓知乎公开页正文。
 * 免费无影平替(个人小规模):登录一次、保存 session、之后复用。
 *
 * ⚠️ 使用须知(务必先读):
 *  - 在【你自己的机器 / 中国网络】上跑。知乎重度封禁境外/机房 IP —— 用你日常上网的 IP。
 *  - 用【你自己的账号】。抓取受知乎 ToS 约束;仅供个人研究、低频、尊重 robots/风控。
 *    不要高频/大规模爬,否则账号可能被限或封。这不是绕过风控的工具,是"手动登录后读页"。
 *  - 抓到的正文用于 MBA 舆情事件时,仍守反捏造:只存 ≤100 字逐字引用 + URL + 时间戳。
 *
 * 安装:
 *   npm init -y && npm i playwright && npx playwright install chromium
 *
 * 首次(手动登录一次,保存会话到 zhihu-state.json):
 *   node zhihu_fetch.mjs login
 *   → 弹出浏览器,你手动登录知乎(短信/扫码/验证码都在这一步人工过),
 *     登录成功后回到终端按 Enter,脚本保存 storageState 退出。
 *
 * 之后(复用会话抓正文,可 headless):
 *   node zhihu_fetch.mjs https://www.zhihu.com/question/361451745/answer/xxxx
 *   node zhihu_fetch.mjs https://zhuanlan.zhihu.com/p/364234140
 *   → 打印:标题 + 正文纯文本(+ 首个可引用短句,便于做 quote)。
 *
 * 会话过期(几周~几月)就重跑 `login` 刷新。
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import readline from 'node:readline';

const STATE = 'zhihu-state.json';
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36';

const arg = process.argv[2];
if (!arg) {
  console.error('用法: node zhihu_fetch.mjs login  |  node zhihu_fetch.mjs <知乎URL>');
  process.exit(1);
}

async function newContext(browser) {
  return browser.newContext({
    userAgent: UA,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    viewport: { width: 1280, height: 900 },
    ...(fs.existsSync(STATE) ? { storageState: STATE } : {}),
  });
}

if (arg === 'login') {
  // 有头浏览器,人工登录一次,保存 storageState
  const browser = await chromium.launch({ headless: false });
  const ctx = await newContext(browser);
  const page = await ctx.newPage();
  await page.goto('https://www.zhihu.com/signin', { waitUntil: 'domcontentloaded' });
  console.log('\n>>> 在弹出的浏览器里手动登录知乎(短信/扫码/验证码都人工过)。');
  console.log('>>> 登录成功、能看到首页后,回到这里按 Enter 保存会话…');
  await new Promise((res) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question('', () => { rl.close(); res(); });
  });
  await ctx.storageState({ path: STATE });
  console.log(`✅ 已保存登录态到 ${STATE}。以后 node zhihu_fetch.mjs <url> 直接复用。`);
  await browser.close();
  process.exit(0);
}

// 抓取模式
if (!fs.existsSync(STATE)) {
  console.error(`✗ 没有 ${STATE}。先跑一次:node zhihu_fetch.mjs login`);
  process.exit(1);
}
const url = arg;
const browser = await chromium.launch({ headless: true });
const ctx = await newContext(browser);
const page = await ctx.newPage();
try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);

  // 反爬/登录墙自检:648B 壳或跳登录页
  const finalUrl = page.url();
  if (/signin|unhuman|captcha/i.test(finalUrl)) {
    console.error(`✗ 被拦到登录/验证页(${finalUrl})。会话可能过期 → 重跑 login;或触发风控 → 降频。`);
    process.exit(2);
  }

  const title = (await page.title()).replace(/ - 知乎$/, '').trim();

  // 正文选择器(知乎回答 / 专栏文章),按优先级尝试
  const selectors = ['.Post-RichText', '.RichContent-inner .RichText', '.RichText', '.QuestionAnswer-content .RichText'];
  let body = '';
  for (const sel of selectors) {
    const el = await page.$(sel);
    if (el) { body = (await el.innerText()).trim(); if (body.length > 80) break; }
  }
  if (!body) body = (await page.evaluate(() => document.body.innerText)).trim();

  const clean = body.replace(/\s+\n/g, '\n').replace(/\n{3,}/g, '\n\n');
  // 首个 ≥10 字的句子,做 quote 候选
  const sent = (clean.match(/[^。！？\n]{10,80}[。！？]/) || [])[0] || clean.slice(0, 60);

  console.log('URL   :', finalUrl);
  console.log('标题  :', title);
  console.log('字数  :', clean.length);
  console.log('quote候选:', sent.trim());
  console.log('\n===== 正文 =====\n');
  console.log(clean.slice(0, 4000));
  if (clean.length > 4000) console.log(`\n…(截断,共 ${clean.length} 字)`);
} catch (e) {
  console.error('✗ 抓取失败:', e.message);
  process.exit(2);
} finally {
  await browser.close();
}
