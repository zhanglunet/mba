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

import os, re, sys, json, glob, time, datetime, argparse

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
# **S 的封闭白名单**(2026-07-25 第 5 次真跑后引入)。
# 第 5 次实测:把 S 定义成开放的「已发生的实质事件」+ 一句「不得用相关性门槛否掉」,
# 模型把「不得否掉」泛化成了「凡是已发生的都别否」——16/17 家 substantive,等于没筛
# (`SIGGRAPH展示已进行`、`网络回滚操作已完成`、`开启 HarmonyOS 升级` 全判了 S)。
# 连续 5 轮在「过严 ↔ 过松」之间摆,说明让 Haiku 级模型做「这件事重不重要」这种**开放判断**
# 本身就不稳。改成**分类**:只能从下面这张封闭清单里挑一个类别,挑不出就是 D。
# 白名单在**代码里**校验(见 _aggregate):模型编一个新类别,一样落成 D。
CATS = {
    "FIN":    "财报/营收/利润/现金流的具体数字已公布",
    "FUND":   "融资 / 投资入股已完成或已签署,且金额明确",
    "MA":     "并购 / 收购 / 剥离已完成或已签约",
    "REG":    "监管处罚 / 禁令 / 判决 / 和解 / 立案调查已下达或已生效",
    "IPO":    "招股书已递交 / 已上市 / 解禁等资本市场程序性里程碑已发生",
    "PEOPLE": "大规模裁员 / 创始人或核心高管变动已落地",
    "CRISIS": "重大安全事故 / 大规模服务中断 / 数据泄露 / 产品召回已发生",
    "PRICE":  "股价大幅异动(有具体幅度)且伴随明确事由",
    "LAUNCH": "全新旗舰产品或模型正式发布且已开放使用",
}

# ── prompt:**逐事件分类**(不是开放判断)──────────────────────────────────────
# 2026-07-25 第 3/4 次真跑的教训:**per-brand 判定会被模型「挑最弱的一条说不」**。
# 第 4 次 A/B(同一份 events.yaml,只换 prompt)实测:per-brand 下模型对 deepseek 判
# directional,引用的是 `039 闭门会实录`——而同一份输入的**第一条**就是 P0
# `027 完成首轮融资:估值超3500亿`(且它一字不差地写在 prompt 的正例里)。
# 根因不是判定标准写得不够细,而是**输出结构允许模型只看一两条就下品牌级结论**。
# 故:模型对**每一条事件**单独出**类别**,品牌 verdict 由代码聚合(任一非 D ⇒ substantive)。
SYSTEM = (
    "你在给一个品牌影响力审计系统做**预筛**。输入是若干品牌各自积压的舆情事件。\n"
    "你的任务:给**输入里的每一条事件**打一个**类别标签**。\n"
    "**逐条打,一条都不能漏**——输出条数必须等于输入事件条数,id 原样照抄。\n\n"
    "**只能从下面这 9 个类别里挑一个**;挑不出就打 D。不许自创类别。\n"
    + "".join(f"  {k} = {v}\n" for k, v in CATS.items()) +
    "  D = 以上都不是\n\n"
    "打 D 的典型(**这些一律 D,不要硬往上面 9 类里塞**):\n"
    "  · 券商评级 / 目标价 / 分析师观点 / 分析评论文章\n"
    "  · 未来时与未确认:'将 / 拟 / 计划 / 预计 / 即将 / 下周 / 明年 / 洽谈中 / 据悉 / 据报道 / 有望 / 曝光'\n"
    "  · **产品规格或参数公布、版本升级、展会演示、评测、营销稿、影像大赛**\n"
    "  · 合作意向 / 联合实验室 / 战略备忘录等**没有明确金额或交割**的合作\n"
    "  · 内部运维动作(如网络回滚、服务扩容)、单件商品成交价、单一商户上下架\n"
    "  · 纯口号、愿景、创始人访谈与闭门会观点\n\n"
    "两条硬规则:\n"
    "1. **已发生 ≠ 值得重审**。事件必须**同时**满足:已经发生、可核验 **且** 命中上面 9 类之一。"
    "「已经发生」但不属于这 9 类的(展会展示、规格发布、版本升级、运维操作),**一律 D**。\n"
    "2. **不要因为「后续结果还没出来」就判成未落地**:『提交招股书』=IPO(已递交),"
    "不是『上市预期』;『FAA 禁止员工购股』=REG(禁令已下达),不是观点。\n\n"
    "你**不判断分数涨跌**,也不建议加减分——只打类别。\n"
    "同一件事被多家转载,**每条都照常单独打**(去重由后续代码做,不用你操心)。\n\n"
    "逐条对照例(取自本项目真实事件):\n"
    "  FUND ←「Deepseek完成首轮融资:估值超3500亿 梁文锋个人持股31%」\n"
    "  FUND ←「AMD投50亿美元入股Anthropic 签2GW芯片大单」\n"
    "  REG  ←「FCC祭出最严禁令:追溯封杀超300家套壳公司」\n"
    "  REG  ←「欧盟委员会依据《数字市场法》处罚谷歌8.9亿欧元」\n"
    "  REG  ←「美法官批准Anthropic 15亿美元版权和解」\n"
    "  IPO  ←「Anthropic提交招股书,冲击万亿美元市值」\n"
    "  FIN  ←「谷歌Q2自由现金流首次转负,上调全年资本开支至最高2050亿美元」\n"
    "  PEOPLE ←「亚马逊3万人大裁员,Nova团队被裁」\n"
    "  CRISIS ←「AWS云服务故障导致大面积互联网瘫痪」\n"
    "  D ←「英伟达在SIGGRAPH展示Vera CPU与Rubin GPU规格」(展会 + 规格公布)\n"
    "  D ←「微软完成网络回滚操作」(内部运维动作)\n"
    "  D ←「华为Mate 80等系列开启HarmonyOS升级」(版本升级)\n"
    "  D ←「爱马仕宣布2027年1月推出高级定制系列」(未来时)\n"
    "  D ←「微软**将**在 Azure 大规模部署 AMD Helios」(『将』=未落地)\n"
    "  D ←「月之暗面以500亿美元估值**洽谈**Pre-IPO融资」(洽谈中)\n"
    "  D ←「英伟达与韩国科学技术院联合成立AI研究实验室」(无金额无交割的合作)\n"
    "  D ←「中金评级上调」(券商观点)\n"
    "  D ←「DJI Osmo Pocket 4 评测」(产品评测)\n\n"
    '只输出一个扁平 JSON 数组(不按品牌嵌套),每项:'
    '{"id":"<原样照抄的事件 id>","k":"<上面 9 个类别之一,或 D>","why":"...(非 D 才写,≤15字)"}。'
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


def _norm_title(t):
    """标题规范化:去掉全部空白与标点。CJK 无词间空格,直接按字符比更稳。"""
    return re.sub(r"[\s\W_]+", "", str(t or ""), flags=re.UNICODE)


def _bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)} or ({s} if s else set())


def _same_story(a, b, thresh=0.65):
    """同一件事?用字符二元组的**重叠系数**(不是 Jaccard)。

    重叠系数 = |A∩B| / min(|A|,|B|):新闻转载常见「一条是另一条的浓缩版」
    (『SpaceX星舰第13次试飞成功,发动机重启、溅落精准…』vs『SpaceX"星舰"完成第13次试飞』),
    长度差距大时 Jaccard 会被长的那条稀释,重叠系数不会。
    **这是启发式,只用于合并展示与计数,不影响 substantive/directional 判定**;
    漏合(如简繁体不同源)只是多列一条,不会改结论。
    """
    A, B = _bigrams(_norm_title(a)), _bigrams(_norm_title(b))
    if not A or not B:
        return False
    return len(A & B) / min(len(A), len(B)) >= thresh


def _aggregate(rows, chunk):
    """**事件级分类** → 品牌级 verdict:任一事件命中白名单类别 ⇒ 该品牌 substantive。

    三道防线,都在代码里(不靠模型自觉):
    1. **白名单校验** —— 类别必须 ∈ CATS,模型自创的类别一律落成 D(第 5 次:开放判断下
       模型把「已发生」等同于「值得重审」,16/17 家 substantive);
    2. **品牌结论由代码聚合** —— 「挑最弱的一条说不」在结构上不可能发生(第 4 次的坑);
    3. **coverage 如实记录** —— 模型漏答按 D 保守处理,但必须看得见,静默漏答比误判更危险。
    """
    owner = {}                      # event id → slug
    for it in chunk:
        for e in it["events"]:
            owner[str(e["id"])] = it["slug"]

    seen = {}                       # event id → (cat, why);cat=None 表示 D
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        eid = str(r.get("id") or "")
        if eid not in owner:        # 模型编的 / 不属本批的 id,丢弃
            continue
        raw = str(r.get("k") or r.get("cat") or "").strip().upper()
        cat = raw if raw in CATS else None      # ← 白名单硬校验
        seen[eid] = (cat, str(r.get("why") or "").strip()[:40])

    out = {}
    for it in chunk:
        ids = [str(e["id"]) for e in it["events"]]
        title = {str(e["id"]): e.get("title", "") for e in it["events"]}
        # 命中白名单的,按 id 升序(id 以日期开头,升序即原发在前)后**同类去重**:
        # 同一件事的多家转载只留最早一条(第 5 次:spacex 的 059/062/063/065 全是「星舰第 13 次试飞」)。
        hits = sorted(i for i in ids if seen.get(i, (None, ""))[0])
        kept, dropped = [], 0
        for i in hits:
            cat, why = seen[i]
            if any(seen[j][0] == cat and _same_story(title.get(j), title.get(i)) for j in kept):
                dropped += 1
                continue
            kept.append(i)

        covered = sum(1 for i in ids if i in seen)
        if kept:
            reason = " · ".join(f"{i}[{seen[i][0]}]" + (f":{seen[i][1]}" if seen[i][1] else "")
                                for i in kept[:4])
            if dropped:
                reason += f"(另 {dropped} 条为同一事件的转载,已合并)"
        else:
            reason = f"{len(ids)} 条事件逐条分类后无一命中白名单"
        if covered < len(ids):
            reason += f"(注:模型只覆盖 {covered}/{len(ids)} 条,未覆盖的按方向价保守处理)"
        out[it["slug"]] = {"verdict": "substantive" if kept else "directional",
                           "reason": reason[:400],
                           "key_event_ids": kept[:8],
                           "categories": sorted({seen[i][0] for i in kept}),
                           "merged_duplicates": dropped,
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
                                   "key_event_ids": [], "categories": [], "merged_duplicates": 0,
                                   "coverage": f"0/{len(it['events'])}"}
    for slug in wanted:  # 兜底:任何漏网的品牌
        out.setdefault(slug, {"verdict": "directional",
                              "reason": "模型未覆盖该品牌 —— 保守判为无实质变化(需人工复核)",
                              "key_event_ids": [], "categories": [], "merged_duplicates": 0,
                              "coverage": "0/0"})
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

    # ── 逐事件分类 + 代码聚合(第 4 次:品牌结论由代码算;第 5 次:类别走封闭白名单)──
    chunk = [{"slug": "x", "events": [{"id": "x-1", "title": "券商上调评级"},
                                      {"id": "x-2", "title": "完成首轮融资估值超3500亿"}]},
             {"slug": "y", "events": [{"id": "y-1", "title": "产品评测"}]}]
    agg = _aggregate([{"id": "x-1", "k": "D", "why": ""},
                      {"id": "x-2", "k": "FUND", "why": "融资完成"},
                      {"id": "y-1", "k": "D", "why": ""}], chunk)
    ok(agg["x"]["verdict"] == "substantive", "aggregate:任一事件命中白名单 ⇒ 品牌 substantive")
    ok(agg["x"]["key_event_ids"] == ["x-2"],
       "aggregate:key_event_ids 只含命中白名单的事件(结构上不可能混入 D)")
    ok(agg["x"]["categories"] == ["FUND"], "aggregate:categories 记录命中了哪些类别")
    ok(agg["y"]["verdict"] == "directional", "aggregate:全 D ⇒ 品牌 directional")
    ok("FUND" in agg["x"]["reason"] and "融资完成" in agg["x"]["reason"],
       "aggregate:reason 带类别与 why,可逐条复核")

    # **第 5 次的核心**:白名单在代码里校验,模型自创类别一律落 D。
    ok(_aggregate([{"id": "x-2", "k": "已发生的实质事件", "why": "很重要"}], chunk)["x"]["verdict"]
       == "directional", "aggregate:模型自创类别 → D(封闭白名单由代码守)")
    ok(_aggregate([{"id": "x-2", "k": "LAUNCH", "why": "旗舰发布"}], chunk)["x"]["verdict"]
       == "substantive", "aggregate:合法类别照常通过")

    # **第 4 次的核心**:哪怕模型只回了最弱的一条,只要另一条命中,品牌就是 substantive。
    ok(_aggregate([{"id": "x-2", "k": "FUND", "why": "融资"}], chunk)["x"]["verdict"] == "substantive",
       "aggregate:模型漏答其余事件也不影响——有命中就是 substantive")

    # 去重:同一件事的多家转载只留最早一条(第 5 次:spacex 星舰试飞 4 条重复)
    dup = [{"slug": "s", "events": [
        {"id": "d-1", "title": "SpaceX星舰第13次试飞成功，发动机重启、溅落精准"},
        {"id": "d-2", "title": "SpaceX“星舰”完成第13次试飞"},
        {"id": "d-3", "title": "欧盟处罚谷歌8.9亿欧元"}]}]
    dd = _aggregate([{"id": "d-1", "k": "LAUNCH", "why": "试飞成功"},
                     {"id": "d-2", "k": "LAUNCH", "why": "试飞成功"},
                     {"id": "d-3", "k": "REG", "why": "处罚落地"}], dup)
    ok(dd["s"]["key_event_ids"] == ["d-1", "d-3"], "aggregate:同类同事去重,只留最早一条")
    ok(dd["s"]["merged_duplicates"] == 1, "aggregate:合并掉几条如实记录")
    ok("已合并" in dd["s"]["reason"], "aggregate:合并要写进 reason(不能静默)")
    ok(_same_story("SpaceX星舰第13次试飞成功，发动机重启、溅落精准", "SpaceX“星舰”完成第13次试飞"),
       "same_story:浓缩版标题能识别为同一件事(重叠系数,不是 Jaccard)")
    ok(not _same_story("欧盟处罚谷歌8.9亿欧元", "SpaceX“星舰”完成第13次试飞"),
       "same_story:不相干的两条不会被误合")

    # 漏答必须**看得见**,不能静默变 directional
    part = _aggregate([{"id": "x-1", "k": "D", "why": ""}], chunk)
    ok(part["x"]["coverage"] == "1/2", "aggregate:coverage 如实记录模型覆盖了几条")
    ok("模型只覆盖 1/2" in part["x"]["reason"], "aggregate:未全覆盖必须写进 reason(不许静默)")
    ok(part["y"]["coverage"] == "0/1", "aggregate:一条没答的品牌 coverage=0")

    ok(_aggregate([{"id": "编造的-id", "k": "FUND", "why": "x"}], chunk)["x"]["verdict"] == "directional",
       "aggregate:模型编造的事件 id 被丢弃(不能凭空造依据)")

    md = render_md({"generated_at": "t", "model": "m", "brands": part})
    ok("逐事件覆盖率:1/3" in md and "⚠ 未全覆盖" in md, "render:摘要必须显示覆盖率与未覆盖告警")

    ok("不判断分数" in SYSTEM, "prompt:明确禁止判断分数涨跌")

    # ↓ 锁住逐事件契约本身(退回 per-brand = 自检红)↓
    ok("每一条事件" in SYSTEM and "一条都不能漏" in SYSTEM,
       "prompt:必须要求逐条判定、不许漏(per-brand 会被『挑最弱的说不』)")
    ok("输出条数必须等于输入事件条数" in SYSTEM, "prompt:输出条数 == 输入条数")
    ok('"id"' in SYSTEM and '"k"' in SYSTEM and "扁平" in SYSTEM,
       "prompt:输出契约是扁平的事件级数组(不按品牌嵌套)")

    # ↓ 第 5 次:S 必须是**封闭白名单分类**,不是开放判断 ↓
    ok(len(CATS) == 9, "白名单:9 个类别(改动数量必须同步改 prompt 里的『这 9 个类别』)")
    ok("只能从下面这 9 个类别里挑一个" in SYSTEM and "不许自创类别" in SYSTEM,
       "prompt:封闭白名单,不许自创类别")
    for code in CATS:
        ok(f"  {code} = " in SYSTEM, f"prompt:类别 {code} 的定义在 prompt 里(代码与 prompt 不能漂移)")
    ok("已发生 ≠ 值得重审" in SYSTEM,
       "prompt:显式打断「已发生⇒值得重审」这条推理(第 5 次 16/17 家的根因)")
    # 第 5 次的四条假阳性,必须逐条出现在 D 的对照例里
    for kw, name in [("SIGGRAPH", "nvidia 展会+规格"), ("网络回滚", "microsoft 运维动作"),
                     ("HarmonyOS升级", "huawei 版本升级"), ("2027年1月", "hermes 未来时")]:
        ok(kw in SYSTEM, f"prompt:第 5 次的假阳性进了 D 对照例 —— {name}")

    # ↓ 锁住第 3/4 次真跑的误判;假阴性最危险 ↓
    ok("已递交" in SYSTEM and "已下达" in SYSTEM,
       "prompt:程序性里程碑已完成(招股书已递交 / 禁令已下达)命中白名单")
    ok("后续结果还没出来" in SYSTEM, "prompt:显式禁止「后续结果没出来⇒判成未落地」这条错误推理")
    ok("计划" in SYSTEM and "将" in SYSTEM and "洽谈" in SYSTEM and "据悉" in SYSTEM,
       "prompt:未来时/未确认(将/计划/洽谈/据悉)= D")
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
