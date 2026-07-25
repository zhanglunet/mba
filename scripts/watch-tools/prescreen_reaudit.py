#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L1 预筛:哪些「建议重审」的品牌**真的值得**跑全量重审?

## 为什么要这个

每日流水线(discover → classify → fold)天天往 events.yaml 堆事件,触发器(P0≥1 / P1≥3 /
加权≥6)很快就被顶过,于是首页常年一片「建议重审」。但 2026-07 那轮 15 家全量重审的实测
结果是:**净持平 1 家、其余多为 ±1~3 分**——大量事件是「方向价」(券商观点 / 预览 /
洽谈 / 同一件事的多家转载),**根本不该改分**。

全量重审(L2)每家要读 report.md 全文 + 全部未消费事件 ≈ 25k token 输入。若天天全量跑,
绝大多数 token 花在得出「↔ 不动」上。**L1 就是那道便宜的闸**:只看事件标题 + severity
(~2k token),判断这批里有没有**已落地的硬事实**;没有就不必惊动 L2。

## 边界(与本项目的反捏造原则一致)

- L1 **只判断「值不值得人去重审」,绝不建议加减分**——分数只在评委 in-character 重打时变。
- 判断是 **model-judged**,输出里如实标注,并要求模型**引用具体事件 id** 以便复核。
- 产出是**建议数据**(`watch/prescreen.json`),给人看 / 给后续消费;**不自动改任何已发布内容**。
- 没有 API key 时**优雅跳过**(退出 0,不写文件),与 classify_candidates 的行为一致。

## 用法

    python3 scripts/watch-tools/prescreen_reaudit.py                # 跑(需 key)
    python3 scripts/watch-tools/prescreen_reaudit.py --dry-run      # 只打印将发给模型的输入 + token 估算,不花钱
    python3 scripts/watch-tools/prescreen_reaudit.py --selftest     # 离线自检(mock 模型返回)
    python3 scripts/watch-tools/prescreen_reaudit.py --brand apple  # 只看一个品牌
"""

import os, sys, json, glob, time, datetime, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import classify_candidates as cc          # 复用 provider 分派 / 退避重试 / JSON 抽取
import evaluate_triggers as et            # 复用 30 天窗口触发规则

OUT_PATH = os.path.join(ROOT, "watch", "prescreen.json")
WATCH_DIR = os.path.join(ROOT, "watch")

# ── 批量与限流(两次真跑调出来的)────────────────────────────────────────────
# 2026-07-25 第 1 次:17 家一次 → 输出撞 max_tokens=2000 被截断(JSONDecodeError)。
# 2026-07-25 第 2 次:改按「品牌数」分批(6 家/批)仍全批超时 —— 因为 **payload 大小取决于
#   事件数,不是品牌数**:6 家 × 平均 30 条 = 195 条/批 ≈ 11.5k token,90s timeout 扛不住。
# 故:① 按**事件数**分批;② 每品牌**限量**且 P0/P1 优先(预筛只需判断「有没有硬事实」,
#   看最重要的十几条足够,不必喂全部);③ 标题截短;④ timeout 加大。
BATCH_EVENTS = 70          # 每批事件数上限(≈6k 字符 ≈3k token 输入)
MAX_EVENTS_PER_BRAND = 18  # 每品牌最多喂多少条(按 P0>P1>P2、同级新→旧取头部)
TITLE_CHARS = 70           # 标题截断:预筛判"类型"够用,不需要完整标题
MAX_TOKENS = 4000
TIMEOUT = 180              # 单次调用超时(默认 90 太紧)
OUT_CHARS_PER_BRAND = 175  # 单品牌输出经验值,供 --dry-run 估算
_SEV_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

SYSTEM = (
    "你在给一个品牌影响力审计系统做**预筛**:判断某品牌积压的舆情信号里,有没有值得"
    "「请人类评委重新打分」的**已落地硬事实**。\n\n"
    "判定标准——\n"
    "substantive(值得重审):**已经发生、可核验**的实质事件。包括两类:\n"
    "  (a) 结果类:财报/营收/盈亏具体数字、融资完成(含估值)、产品正式发布并可用、"
    "裁员/高管变动落地、监管处罚或诉讼判决、股价异动伴随明确事由;\n"
    "  (b) **程序性里程碑已完成**:招股书/文件**已递交**、禁令/规定**已下达**、处罚**已生效**、"
    "合作**已签约**、许可**已获批**、机构**已设立**——这些是既成法律/行政事实,**不要因为"
    "「后续结果还没出来」就判成预期**(例:『提交招股书』是已发生的事实,不是『上市预期』;"
    "『FAA 禁止员工购股』是已下达的规定,不是观点)。\n"
    "directional(不值得):只有**方向价**——券商评级/目标价/分析师观点、"
    "'据报道/洽谈中/预计/拟/计划/**将**/预览/即将/有望'、分析与评测文章、"
    "同一件事的多家转载、纯口号或愿景表述。\n\n"
    "重要:\n"
    "1. 你**不判断分数涨跌**,也不建议加减分——只回答「值不值得人去重审」。\n"
    "2. 同一件事被多家转载,算**一件**;若该事件本身只是观点,再多转载也仍是 directional。\n"
    "3. **相关性门槛**:硬事实还要**可能影响品牌影响力**(市场份额/定价权/护城河/"
    "用户信任/品牌身份)才算 substantive。真实但边缘的事(如成立一个联合实验室、"
    "单件商品拍卖成交价)**不足以单独触发重审**。\n"
    "4. reason 必须**引用具体事件 id**(取自输入),不要泛泛而谈;控制在 60 字内。\n"
    "5. **key_event_ids 只能放 substantive 的依据**,不许混入 directional 事件"
    "(例:『以 500 亿估值**洽谈**融资』是 directional,不能当依据)。\n\n"
    "对照例(取自本项目真实事件):\n"
    "  substantive ✓「Anthropic提交招股书,冲击万亿美元市值」(招股书已递交=既成事实)\n"
    "  substantive ✓「FAA禁止员工购买SpaceX股份」(禁令已下达)\n"
    "  substantive ✓「完成首轮融资,估值超3500亿,梁文锋持股31%」(融资完成+具体数字)\n"
    "  directional ✗「微软**将**在 Azure 大规模部署 AMD Helios」(『将』=未落地)\n"
    "  directional ✗「月之暗面以500亿美元估值**洽谈**Pre-IPO融资」(洽谈中)\n"
    "  directional ✗「英伟达与韩国科学技术院联合成立AI研究实验室」(真实但对品牌影响力权重过低)\n"
    "  directional ✗「中金评级上调」(券商观点)\n\n"
    '只输出 JSON 数组,每项:{"slug":"...","verdict":"substantive|directional",'
    '"reason":"...(≤60字,含事件 id)","key_event_ids":["..."]}。不要任何解释性散文。'
)


def _events_digest(events, window_days=30, as_of=None, limit=MAX_EVENTS_PER_BRAND):
    """窗口内未消费事件 → (id, date, sev, title);只给标题,不给正文/URL,省 token。

    **按 P0>P1>P2、同级日期新→旧取前 `limit` 条**:预筛只判断「有没有已落地的硬事实」,
    喂最重要的十几条足够;全喂会让单批 payload 撑到 11k+ token 而超时(2026-07-25 实测)。
    优先级排序保证「限量」不会把 P0 挤掉。
    """
    dates = [et.as_date(e.get("date")) for e in events if isinstance(e, dict)]
    dates = [d for d in dates if d]
    if as_of is None:
        as_of = max(dates) if dates else datetime.date.today()
    start = as_of - datetime.timedelta(days=window_days)
    rows = []
    for e in events:
        if not isinstance(e, dict) or e.get("consumed_by"):
            continue
        d = et.as_date(e.get("date"))
        if d is None or not (start <= d <= as_of):
            continue
        rows.append((_SEV_RANK.get(e.get("severity"), 9), -d.toordinal(),
                     {"id": e.get("id"), "date": str(e.get("date")),
                      "sev": e.get("severity"), "title": (e.get("title") or "")[:TITLE_CHARS]}))
    rows.sort(key=lambda r: (r[0], r[1]))
    return [r[2] for r in rows[:limit]]


def build_payload(brand=None, window_days=30):
    """→ [{slug, triggered_by, events:[...]}] ,只含**触发了**重审规则的品牌。"""
    feeds = et.load_events(WATCH_DIR, brand=brand)
    items = []
    for slug, events in sorted(feeds.items()):
        res = et.evaluate(events, as_of=None) if _accepts_none(et.evaluate) else None
        if res is None:  # evaluate 需要显式 as_of
            dates = [et.as_date(e.get("date")) for e in events if isinstance(e, dict)]
            dates = [d for d in dates if d]
            as_of = max(dates) if dates else datetime.date.today()
            res = et.evaluate(events, as_of, window_days)
        if not res.get("hit"):
            continue
        digest = _events_digest(events, window_days)
        if not digest:
            continue
        items.append({"slug": slug, "triggered_by": res.get("rules") or res.get("hit"),
                      "events": digest})
    return items


def _accepts_none(fn):
    return False  # evaluate 需要显式 as_of;保留分支以便将来放宽


def _clean(rows, wanted_slugs):
    """规范化模型返回:verdict 只允许两值;未覆盖的品牌降级为 directional 并标注。"""
    by = {}
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        slug = r.get("slug")
        if slug not in wanted_slugs:
            continue
        v = r.get("verdict")
        if v not in ("substantive", "directional"):
            v = "directional"
        # reason 上限 220:prompt 要 ≤60 字,但 reason 里还要带事件 id(单个 id ≈ 25 字符),
        # 160 会把「60 字正文 + 2~3 个 id」截在半个词上(2026-07-25 kimichat 实测)。
        by[slug] = {"verdict": v, "reason": str(r.get("reason") or "")[:220],
                    "key_event_ids": [str(i) for i in (r.get("key_event_ids") or [])][:6]}
    for slug in wanted_slugs:
        by.setdefault(slug, {"verdict": "directional",
                             "reason": "模型未覆盖该品牌 —— 保守判为无实质变化(需人工复核)",
                             "key_event_ids": []})
    return by


def _chunks(items, max_events=BATCH_EVENTS):
    """按**事件数**切批(而非品牌数)—— payload 大小取决于事件数。单家超限时自成一批。"""
    out, cur, n = [], [], 0
    for it in items:
        k = len(it["events"])
        if cur and n + k > max_events:
            out.append(cur)
            cur, n = [], 0
        cur.append(it)
        n += k
    if cur:
        out.append(cur)
    return out


def run(items, prov, max_events=BATCH_EVENTS):
    """分批调用,汇总。

    **两处都是 2026-07-25 首次真跑踩出来的**:
    1. 必须显式传 `system=SYSTEM` —— 否则 `cc.call_llm` 会用 classify_candidates 的模块级
       SYSTEM(那是「给事件分 dim/severity」的 prompt),模型会答错题;
    2. 必须分批 + 调大 max_tokens —— 17 家一次要输出 17 个含 reason 的对象,撞上默认
       max_tokens=2000 被截断,报裸 JSONDecodeError。
    单批失败**不拖垮整体**:该批品牌降级为 directional 并标注,其余批次结果照常返回。
    """
    out, wanted = {}, {it["slug"] for it in items}
    batches = _chunks(items, max_events)
    for bi, chunk in enumerate(batches):
        if bi:
            time.sleep(float(cc._env("MBA_CLASSIFY_BATCH_PAUSE", "2")))  # 避开端点 QPS 限流
        payload = [{"slug": it["slug"], "events": it["events"]} for it in chunk]
        slugs = {it["slug"] for it in chunk}
        try:
            rows = cc.call_llm(payload, prov, system=SYSTEM, max_tokens=MAX_TOKENS, timeout=TIMEOUT)
            out.update(_clean(rows, slugs))
        except Exception as e:  # 单批失败:保守降级,继续跑其余批
            print(f"prescreen: 第 {bi + 1}/{len(batches)} 批失败({e})—— 该批降级为 directional。",
                  file=sys.stderr)
            for slug in slugs:
                out[slug] = {"verdict": "directional",
                             "reason": f"本批模型调用失败,保守判为无实质变化(需人工复核):{str(e)[:60]}",
                             "key_event_ids": []}
    for slug in wanted:  # 兜底:任何漏网的品牌
        out.setdefault(slug, {"verdict": "directional",
                              "reason": "模型未覆盖该品牌 —— 保守判为无实质变化(需人工复核)",
                              "key_event_ids": []})
    return out


def render_md(result):
    """人可读摘要(给 PR body / 终端)。"""
    sub = [s for s, r in result["brands"].items() if r["verdict"] == "substantive"]
    dirn = [s for s, r in result["brands"].items() if r["verdict"] == "directional"]
    lines = [f"L1 预筛 · {result['generated_at']} · model={result['model']}",
             f"触发品牌 {len(result['brands'])} 家 → **值得重审 {len(sub)} 家** / 仅方向价 {len(dirn)} 家", ""]
    for slug in sub:
        r = result["brands"][slug]
        lines.append(f"  ⚡ {slug}: {r['reason']}  [{', '.join(r['key_event_ids'])}]")
    for slug in dirn:
        lines.append(f"  · {slug}: {result['brands'][slug]['reason']}")
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(description="L1:预筛哪些触发品牌真的值得全量重审")
    ap.add_argument("--brand", help="只看一个品牌")
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true", help="只打印将发给模型的输入 + token 估算,不调用")
    ap.add_argument("--selftest", action="store_true", help="离线自检(mock 模型返回)")
    ap.add_argument("-o", "--out", default=OUT_PATH)
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    items = build_payload(args.brand, args.window_days)
    if not items:
        print("prescreen: 无触发品牌 —— 无需预筛。")
        return 0

    if args.dry_run:
        payload = [{"slug": it["slug"], "events": it["events"]} for it in items]
        blob = json.dumps(payload, ensure_ascii=False)
        n_ev = sum(len(it["events"]) for it in items)
        batches = _chunks(items)
        print(f"prescreen --dry-run:{len(items)} 个触发品牌 / {n_ev} 条事件"
              f"(每品牌 ≤{MAX_EVENTS_PER_BRAND} 条,P0/P1 优先)→ 分 {len(batches)} 批"
              f"(每批 ≤{BATCH_EVENTS} 条事件)")
        print(f"  输入合计 ≈ {len(blob)} 字符 + system {len(SYSTEM)}×{len(batches)} "
              f"≈ {(len(blob) + len(SYSTEM) * len(batches)) // 2} token(粗估,中文 ~2 字符/token)")
        # 逐批打印:两次真跑的失败都出在**单批**过大(截断 / 超时),总量反而不是关键。
        for i, ch in enumerate(batches, 1):
            c = len(json.dumps([{"slug": x["slug"], "events": x["events"]} for x in ch], ensure_ascii=False))
            oc = len(ch) * OUT_CHARS_PER_BRAND
            print(f"    批{i}: {len(ch)} 家 / {sum(len(x['events']) for x in ch)} 条 / "
                  f"入 ≈{c // 2} token · 出 ≈{oc // 2} token(上限 {MAX_TOKENS},timeout {TIMEOUT}s)")
        print(f"  品牌:{', '.join(it['slug'] for it in items)}")
        return 0

    prov = cc._provider()
    if not prov:
        print("prescreen: 未配置 GLM_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY —— 优雅跳过。")
        return 0

    brands = run(items, prov)
    result = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": prov[3],
        "window_days": args.window_days,
        "note": ("L1 预筛:判断「值不值得请评委重审」,**不判断分数涨跌**。verdict 为 model-judged,"
                 "reason 引用事件 id 供复核;分数只在评委 in-character 重打时变。"),
        "brands": brands,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(render_md(result))
    print(f"\nprescreen: 已写 {os.path.relpath(args.out, ROOT)}")
    return 0


def _selftest():
    """离线断言:不碰网络,验证摘要/规范化/降级/窗口这几处易错的地方。"""
    checks, fails = 0, []

    def ok(cond, name):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(name)

    today = datetime.date(2026, 7, 25)
    ev = [
        {"id": "a-1", "date": today, "severity": "P1", "title": "完成 B 轮融资 10 亿美元"},
        {"id": "a-2", "date": today, "severity": "P2", "title": "券商上调评级", "consumed_by": "v3"},
        {"id": "a-3", "date": datetime.date(2026, 1, 1), "severity": "P0", "title": "很久以前的事"},
    ]
    d = _events_digest(ev, 30, as_of=today)
    ok(len(d) == 1 and d[0]["id"] == "a-1", "digest:只取窗口内未消费")
    ok("title" in d[0] and "url" not in d[0], "digest:不含 URL(省 token)")

    # 限量必须 P0 优先 —— 否则"每品牌 ≤18 条"可能把 P0 挤掉(2026-07-25 超时修复引入)
    many = ([{"id": f"p2-{i}", "date": today, "severity": "P2", "title": "小事"} for i in range(30)]
            + [{"id": "p0-x", "date": today - datetime.timedelta(days=20), "severity": "P0", "title": "大事"}])
    dd = _events_digest(many, 30, as_of=today, limit=5)
    ok(len(dd) == 5, "digest:限量生效")
    ok(dd[0]["id"] == "p0-x", "digest:P0 优先(限量不会挤掉最重要的)")

    ok(len(_chunks([{"slug": "a", "events": [0] * 50}, {"slug": "b", "events": [0] * 50}],
                   max_events=70)) == 2, "chunks:按事件数切批(不是品牌数)")
    ok(len(_chunks([{"slug": "a", "events": [0] * 200}], max_events=70)) == 1, "chunks:单家超限自成一批")

    cleaned = _clean([{"slug": "x", "verdict": "substantive", "reason": "见 a-1", "key_event_ids": ["a-1"]}],
                     {"x", "y"})
    ok(cleaned["x"]["verdict"] == "substantive", "clean:保留合法 verdict")
    ok(cleaned["y"]["verdict"] == "directional", "clean:未覆盖品牌保守降级")
    ok("需人工复核" in cleaned["y"]["reason"], "clean:降级理由写明需复核")

    bad = _clean([{"slug": "x", "verdict": "涨分!", "reason": "r"}], {"x"})
    ok(bad["x"]["verdict"] == "directional", "clean:非法 verdict 降级(模型不能自创判定)")

    ok("不判断分数" in SYSTEM and "directional" in SYSTEM, "prompt:明确禁止判断分数涨跌")
    ok("转载" in SYSTEM, "prompt:明确同一事多家转载算一件")

    # ↓ 四条锁住 2026-07-25 第 3 次真跑的误判(见 docs/16 §9.5)↓
    # 假阴性最危险:「提交招股书」「FAA 下达禁令」都被判成"预期/观点"而漏掉。
    ok("程序性里程碑" in SYSTEM and "已递交" in SYSTEM and "已下达" in SYSTEM,
       "prompt:程序性里程碑已完成 = substantive(招股书已递交 / 禁令已下达)")
    ok("后续结果还没出来" in SYSTEM,
       "prompt:显式禁止「后续结果没出来⇒判成预期」这条错误推理")
    # 假阳性:「微软**将**在 Azure 部署」被判 substantive。
    ok("计划" in SYSTEM and "将" in SYSTEM and "洽谈" in SYSTEM,
       "prompt:未来时(将/计划/洽谈)= directional")
    ok("相关性门槛" in SYSTEM and "品牌影响力" in SYSTEM,
       "prompt:相关性门槛(真实但边缘的事不足以单独触发重审)")
    ok("key_event_ids 只能放 substantive" in SYSTEM,
       "prompt:key_event_ids 不许混入 directional 事件")
    ok(SYSTEM.count("substantive ✓") >= 3 and SYSTEM.count("directional ✗") >= 3,
       "prompt:两类各 ≥3 个 few-shot 对照例(取自真实事件)")

    # ↓ 两条锁住 2026-07-25 首次真跑踩到的 bug ↓
    import inspect
    sig = inspect.signature(cc.call_llm).parameters
    ok("system" in sig and "max_tokens" in sig,
       "call_llm:必须支持覆盖 system/max_tokens(否则复用时会用错 prompt / 被截断)")
    src = inspect.getsource(run)
    ok("system=SYSTEM" in src,
       "run:必须显式传自己的 SYSTEM(不传会用成 classify 的分类 prompt,答错题)")
    ok("max_tokens=MAX_TOKENS" in src, "run:必须调大 max_tokens(17 家一次会被 2000 截断)")
    ok("timeout=TIMEOUT" in src, "run:必须加大 timeout(默认 90s 扛不住大 payload)")
    ok("_chunks(" in src, "run:必须按事件数分批(按品牌数分会撑爆单批)")
    ok("timeout" in inspect.signature(cc.call_llm).parameters, "call_llm:必须支持覆盖 timeout")

    # 单批失败不拖垮整体:mock 一个必炸的 call_llm
    real = cc.call_llm
    try:
        cc.call_llm = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        got = run([{"slug": "a", "events": [0]}, {"slug": "b", "events": [0]}],
                  ("x", "k", "u", "m"), max_events=1)
        ok(set(got) == {"a", "b"} and all(v["verdict"] == "directional" for v in got.values()),
           "run:单批失败→该批降级为 directional,不抛异常")
        ok("需人工复核" in got["a"]["reason"], "run:失败降级理由写明需复核")
    finally:
        cc.call_llm = real

    r = {"generated_at": "t", "model": "m",
         "brands": {"a": {"verdict": "substantive", "reason": "见 a-1", "key_event_ids": ["a-1"]},
                    "b": {"verdict": "directional", "reason": "只有观点", "key_event_ids": []}}}
    md = render_md(r)
    ok("值得重审 1 家" in md and "⚡ a" in md, "render:摘要区分两类")

    print(f"prescreen --selftest: {'✅ ' + str(checks) + ' 组断言全部通过(门禁有牙)' if not fails else '❌ 失败: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
