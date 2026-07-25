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
# 2026-07-25 第 4 次:改**逐事件判定**后,输出规模从「每品牌一行」变成「每事件一行」,
#   故批量减半(70→40),保证单批输出 ≈1k token,离 MAX_TOKENS 还有大余量。
BATCH_EVENTS = 40          # 每批事件数上限(≈3.5k 字符 ≈1.8k token 输入 / ≈1k token 输出)
MAX_EVENTS_PER_BRAND = 18  # 每品牌最多喂多少条(按 P0>P1>P2、同级新→旧取头部)
TITLE_CHARS = 70           # 标题截断:预筛判"类型"够用,不需要完整标题
MAX_TOKENS = 4000
TIMEOUT = 180              # 单次调用超时(默认 90 太紧)
# 逐事件判定后,输出规模按**事件数**算(不再按品牌数):
# 单条 {"id":"2026-07-19-deepseek-027","v":"D","why":""} ≈ 48 字符;S 条多带 ≤20 字 why,取 60。
OUT_CHARS_PER_EVENT = 60   # 单事件输出经验值,供 --dry-run 估算
_SEV_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

# ── prompt:**逐事件**判定 ────────────────────────────────────────────────────
# 2026-07-25 第 3/4 次真跑的教训:**per-brand 判定会被模型「挑最弱的一条说不」**。
# 第 4 次 A/B(同一份 events.yaml,只换 prompt)实测:per-brand 下模型对 deepseek 判
# directional,引用的是 `039 闭门会实录`——而同一份输入的**第一条**就是 P0
# `027 完成首轮融资:估值超3500亿`(且它一字不差地写在 prompt 的正例里)。
# 同类漏判还有 dji(P0 FCC 禁令)、google(欧盟罚 8.9 亿)、anthropic(P0 赔 15 亿)。
# 根因不是判定标准写得不够细,而是**输出结构允许模型只看一两条就下品牌级结论**。
# 故改成:模型对**每一条事件**单独出判定,品牌 verdict 由代码聚合(任一 S ⇒ substantive)。
# 这样「挑最弱的说不」在结构上不可能发生,且每条判定都能被人逐条复核。
SYSTEM = (
    "你在给一个品牌影响力审计系统做**预筛**。输入是若干品牌各自积压的舆情事件。\n"
    "你的任务:对**输入里的每一条事件**单独判定它是不是**已落地的硬事实**。\n"
    "**逐条判,一条都不能漏**——输出条数必须等于输入事件条数,id 原样照抄。\n\n"
    "S = substantive(已落地硬事实):**已经发生、可核验**的实质事件。两类:\n"
    "  (a) 结果类:财报/营收/现金流具体数字、融资完成(含估值)、产品正式发布并可用、"
    "裁员/高管变动落地、监管处罚、诉讼判决或和解、股价异动伴随明确事由;\n"
    "  (b) **程序性里程碑已完成**:招股书/文件**已递交**、禁令/规定**已下达**、处罚**已生效**、"
    "合作**已签约**、许可**已获批**——既成法律/行政事实。**不要因为「后续结果还没出来」"
    "就判成预期**(『提交招股书』是已发生的事实,不是『上市预期』;『FAA 禁止员工购股』"
    "是已下达的规定,不是观点)。\n"
    "D = directional(只有方向价):券商评级/目标价/分析师观点、"
    "'据报道/据悉/洽谈中/预计/拟/计划/**将**/预览/即将/有望/曝光/被视为'、"
    "分析评论与产品评测、营销稿与影像大赛、纯口号或愿景表述。\n\n"
    "重要:\n"
    "1. 你**不判断分数涨跌**,也不建议加减分——只判断每条事件是 S 还是 D。\n"
    "2. **相关性门槛只用来排除明显边缘的事**(如成立一个联合实验室、单件商品拍卖成交价、"
    "单一商户下架)。**财报数字 / 监管处罚 / 禁令 / 融资完成 / 诉讼和解 / 大额投资入股"
    "一律判 S,不得用相关性门槛否掉。**\n"
    "3. 同一件事被多家转载,**每条都照常单独判**(去重由后续代码做,不用你操心)。\n"
    "4. 只有 v=\"S\" 的才写 why(≤20 字,说清楚落地的是什么);v=\"D\" 的 why 留空字符串。\n\n"
    "逐条对照例(取自本项目真实事件):\n"
    "  S ✓「Deepseek完成首轮融资:估值超3500亿 梁文锋个人持股31%」(融资完成+具体数字)\n"
    "  S ✓「FCC祭出最严禁令:追溯封杀超300家套壳公司」(禁令已下达)\n"
    "  S ✓「欧盟委员会依据《数字市场法》处罚谷歌8.9亿欧元」(处罚已落地)\n"
    "  S ✓「Anthropic提交招股书,冲击万亿美元市值」(招股书已递交)\n"
    "  S ✓「美法官批准Anthropic 15亿美元版权和解」(和解已生效)\n"
    "  S ✓「AMD投50亿美元入股Anthropic 签2GW芯片大单」(投资入股已宣布,金额明确)\n"
    "  D ✗「微软**将**在 Azure 大规模部署 AMD Helios」(『将』=未落地)\n"
    "  D ✗「月之暗面以500亿美元估值**洽谈**Pre-IPO融资」(洽谈中)\n"
    "  D ✗「SpaceX**据悉**暂停部分猎鹰9号预订」(『据悉』=未确认)\n"
    "  D ✗「英伟达与韩国科学技术院联合成立AI研究实验室」(边缘,权重过低)\n"
    "  D ✗「中金评级上调」(券商观点)\n"
    "  D ✗「DJI Osmo Pocket 4 评测」(产品评测)\n\n"
    '只输出一个扁平 JSON 数组(不按品牌嵌套),每项:'
    '{"id":"<原样照抄的事件 id>","v":"S"|"D","why":"...(仅 S 需要,≤20字)"}。'
    "不要任何解释性散文。"
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


def _aggregate(rows, chunk):
    """**事件级**判定 → 品牌级 verdict:任一事件 S ⇒ 该品牌 substantive。

    品牌结论由**代码**聚合,不由模型给——这正是「挑最弱的一条说不」在结构上不可能发生的原因。
    模型漏答的事件按 directional 记(保守),但**记进 coverage 并在摘要里显示**:
    静默的漏答比误判更危险,必须看得见。
    """
    owner = {}                      # event id → slug
    for it in chunk:
        for e in it["events"]:
            owner[str(e["id"])] = it["slug"]

    seen = {}                       # event id → (verdict, why)
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        eid = str(r.get("id") or "")
        if eid not in owner:        # 模型编的 / 不属本批的 id,丢弃
            continue
        raw = str(r.get("v") or r.get("verdict") or "").strip().upper()
        v = "substantive" if raw.startswith("S") else "directional"
        seen[eid] = (v, str(r.get("why") or "").strip()[:40])

    out = {}
    for it in chunk:
        ids = [str(e["id"]) for e in it["events"]]
        subs = [(i, seen[i][1]) for i in ids if seen.get(i, ("directional", ""))[0] == "substantive"]
        covered = sum(1 for i in ids if i in seen)
        if subs:
            reason = " · ".join(f"{i}:{w}" if w else i for i, w in subs[:4])
        else:
            reason = f"{len(ids)} 条事件逐条判定后全为方向价"
        if covered < len(ids):
            reason += f"(注:模型只覆盖 {covered}/{len(ids)} 条,未覆盖的按方向价保守处理)"
        out[it["slug"]] = {"verdict": "substantive" if subs else "directional",
                           "reason": reason[:400],
                           "key_event_ids": [i for i, _ in subs][:8],
                           "coverage": f"{covered}/{len(ids)}"}
    return out


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
        try:
            rows = cc.call_llm(payload, prov, system=SYSTEM, max_tokens=MAX_TOKENS, timeout=TIMEOUT)
            out.update(_aggregate(rows, chunk))
        except Exception as e:  # 单批失败:保守降级,继续跑其余批
            print(f"prescreen: 第 {bi + 1}/{len(batches)} 批失败({e})—— 该批降级为 directional。",
                  file=sys.stderr)
            for it in chunk:
                out[it["slug"]] = {"verdict": "directional",
                                   "reason": f"本批模型调用失败,保守判为无实质变化(需人工复核):{str(e)[:60]}",
                                   "key_event_ids": [], "coverage": f"0/{len(it['events'])}"}
    for slug in wanted:  # 兜底:任何漏网的品牌
        out.setdefault(slug, {"verdict": "directional",
                              "reason": "模型未覆盖该品牌 —— 保守判为无实质变化(需人工复核)",
                              "key_event_ids": [], "coverage": "0/0"})
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
    # 覆盖率:逐事件判定下,模型漏答会静默变成 directional —— 必须让它看得见。
    cov = [r.get("coverage", "") for r in result["brands"].values()]
    done = sum(int(c.split("/")[0]) for c in cov if "/" in c)
    total = sum(int(c.split("/")[1]) for c in cov if "/" in c)
    if total:
        bad = [s for s, r in result["brands"].items()
               if "/" in r.get("coverage", "") and r["coverage"].split("/")[0] != r["coverage"].split("/")[1]]
        lines += ["", f"逐事件覆盖率:{done}/{total}"
                      + (f" ⚠ 未全覆盖:{', '.join(bad)}(未覆盖的按方向价保守处理)" if bad else " ✅ 全覆盖")]
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
            n = sum(len(x["events"]) for x in ch)
            oc = n * OUT_CHARS_PER_EVENT          # 逐事件判定:输出条数 == 输入事件条数
            print(f"    批{i}: {len(ch)} 家 / {n} 条 / "
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

    # ── 逐事件聚合(2026-07-25 第 4 次改造:品牌结论由代码算,不由模型给)────────────
    chunk = [{"slug": "x", "events": [{"id": "x-1"}, {"id": "x-2"}]},
             {"slug": "y", "events": [{"id": "y-1"}]}]
    agg = _aggregate([{"id": "x-1", "v": "D", "why": ""},
                      {"id": "x-2", "v": "S", "why": "融资完成"},
                      {"id": "y-1", "v": "D", "why": ""}], chunk)
    ok(agg["x"]["verdict"] == "substantive", "aggregate:任一事件 S ⇒ 品牌 substantive")
    ok(agg["x"]["key_event_ids"] == ["x-2"],
       "aggregate:key_event_ids 只含 S 事件(结构上不可能混入 directional)")
    ok(agg["y"]["verdict"] == "directional", "aggregate:全 D ⇒ 品牌 directional")
    ok("融资完成" in agg["x"]["reason"], "aggregate:reason 由 S 事件的 why 拼出,可逐条复核")

    # **本次改造的核心**:哪怕模型只回了最弱的一条,只要另一条判了 S,品牌就是 substantive。
    # per-brand 时代模型能「挑最弱的说不」;逐事件 + 代码聚合后这条路被堵死。
    ok(_aggregate([{"id": "x-2", "v": "S", "why": "融资完成"}], chunk)["x"]["verdict"] == "substantive",
       "aggregate:模型漏答其余事件也不影响——有 S 就是 substantive")

    # 漏答必须**看得见**,不能静默变 directional
    part = _aggregate([{"id": "x-1", "v": "D", "why": ""}], chunk)
    ok(part["x"]["coverage"] == "1/2", "aggregate:coverage 如实记录模型覆盖了几条")
    ok("模型只覆盖 1/2" in part["x"]["reason"], "aggregate:未全覆盖必须写进 reason(不许静默)")
    ok(part["y"]["coverage"] == "0/1", "aggregate:一条没答的品牌 coverage=0")

    ok(_aggregate([{"id": "编造的-id", "v": "S", "why": "x"}], chunk)["x"]["verdict"] == "directional",
       "aggregate:模型编造的事件 id 被丢弃(不能凭空造依据)")
    ok(_aggregate([{"id": "x-1", "v": "涨分!", "why": ""}], chunk)["x"]["verdict"] == "directional",
       "aggregate:非法 verdict 归为 directional(模型不能自创判定)")

    md = render_md({"generated_at": "t", "model": "m", "brands": part})
    ok("逐事件覆盖率:1/3" in md and "⚠ 未全覆盖" in md, "render:摘要必须显示覆盖率与未覆盖告警")

    ok("不判断分数" in SYSTEM, "prompt:明确禁止判断分数涨跌")

    # ↓ 锁住逐事件契约本身(退回 per-brand = 自检红)↓
    ok("每一条事件" in SYSTEM and "一条都不能漏" in SYSTEM,
       "prompt:必须要求逐条判定、不许漏(per-brand 会被『挑最弱的说不』)")
    ok("输出条数必须等于输入事件条数" in SYSTEM, "prompt:输出条数 == 输入条数")
    ok('"id"' in SYSTEM and '"v"' in SYSTEM and "扁平" in SYSTEM,
       "prompt:输出契约是扁平的事件级数组(不按品牌嵌套)")

    # ↓ 锁住第 3 次真跑的误判(见 docs/16 §9.5);假阴性最危险 ↓
    ok("程序性里程碑" in SYSTEM and "已递交" in SYSTEM and "已下达" in SYSTEM,
       "prompt:程序性里程碑已完成 = S(招股书已递交 / 禁令已下达)")
    ok("后续结果还没出来" in SYSTEM, "prompt:显式禁止「后续结果没出来⇒判成预期」这条错误推理")
    ok("计划" in SYSTEM and "将" in SYSTEM and "洽谈" in SYSTEM and "据悉" in SYSTEM,
       "prompt:未来时/未确认(将/计划/洽谈/据悉)= D")
    # 第 4 次真跑:相关性门槛被模型当成否掉一切的逃生口(欧盟罚款也被否)。必须封边界。
    ok("相关性门槛只用来排除明显边缘的事" in SYSTEM,
       "prompt:相关性门槛只排除边缘事,不是万能否决权")
    ok("不得用相关性门槛否掉" in SYSTEM,
       "prompt:财报数字/监管处罚/禁令/融资完成/诉讼和解 一律 S,不得被相关性门槛否掉")
    ok(SYSTEM.count("S ✓") >= 5 and SYSTEM.count("D ✗") >= 5,
       "prompt:两类各 ≥5 个 few-shot 对照例(取自真实事件)")
    # 第 4 次真跑漏掉的四条硬事实,必须逐条出现在正例里
    for kw, name in [("3500亿", "deepseek 融资完成"), ("FCC", "dji 禁令"),
                     ("8.9亿欧元", "google 欧盟处罚"), ("15亿美元版权和解", "anthropic 和解")]:
        ok(kw in SYSTEM, f"prompt:第 4 次漏判的硬事实进了正例 —— {name}")

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
    ok("_aggregate(" in src, "run:品牌结论必须由代码聚合(模型只出事件级判定)")

    # 输出预算硬算一遍:逐事件判定下,输出条数 == 输入条数,BATCH_EVENTS 调大会直接撞 MAX_TOKENS。
    # 这正是第 1 次真跑被截断、而 --dry-run 没预警的那个洞(它当时只估了输入)。
    ok(BATCH_EVENTS * OUT_CHARS_PER_EVENT // 2 < MAX_TOKENS * 0.6,
       f"预算:单批输出估算({BATCH_EVENTS}×{OUT_CHARS_PER_EVENT}/2)必须远低于 MAX_TOKENS={MAX_TOKENS}")

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
