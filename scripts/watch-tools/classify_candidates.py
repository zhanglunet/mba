#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classify_candidates.py — 用 Claude 给舆情候选**预分类**,产出「建议入库」adopt 文件。

流程(全自动开 PR 的中枢,docs/16 §2.7):
  discover 产出 <date>.json(候选:逐字标题/日期/URL)→ 本脚本逐条问 Claude:
    keep?（值不值得入库,剔除行情/榜单/重复/软文/无关/纯观点）
    dim / severity / direction / lens_map（分类判断,**标 model-judged**）
    confidence + reason
  → 高置信 keep 的写成 watch/_adopt/auto-<date>.yaml(fold_adopt 折入 events.yaml)
  → watch-discover 开 PR,人工只审最终 events.yaml diff 再合并(合并=人工闸门)。

反捏造边界(**硬约束**):
  - quote / title / url / date **原样透传**,脚本与模型都**不改写、不编造**任何引文;
    模型只做「分类」,不生成新的事实文本。
  - direction 等是**显式编辑判断**(direction_by: model-judged),不假装客观。
  - 不改任何审计分数;采纳事件入库后仍由评委在 EVOLUTION 重审时消费。

依赖:仅标准库(urllib)。**多 provider**,按环境变量择一(优先级从上到下):
  - GLM_API_KEY      → 智谱 GLM(OpenAI 兼容,base 默认 https://open.bigmodel.cn/api/paas/v4,
                       模型默认 glm-4-flash);可选 GLM_BASE_URL。
  - OPENAI_API_KEY   → OpenAI 或任意 OpenAI 兼容端点(base 默认官方,可选 OPENAI_BASE_URL,模型默认 gpt-4o-mini)。
  - ANTHROPIC_API_KEY→ Anthropic Messages API(base 默认官方,模型默认 claude-haiku-4-5)。
  用 MBA_CLASSIFY_MODEL 覆盖模型名。**都没设时优雅跳过**(不写 adopt,退回候选流,退出 0)。

用法:
  python3 scripts/watch-tools/classify_candidates.py --in watch/_candidates/<date>.json \
      --adopt watch/_adopt/auto-<date>.yaml --report /tmp/classify.md
  python3 scripts/watch-tools/classify_candidates.py --selftest   # 不联网,自测解析/落盘
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DIMS = [f"W{i}" for i in range(1, 10)]
SEVS = ["P0", "P1", "P2", "P3"]
DIRS = ["pos", "neg", "neutral", "mixed"]
LENSES = ["origin", "category", "leverage", "identity", "signal"]
BATCH = 18

# 多 provider:按环境变量存在与否择一(GLM 优先,再 OpenAI 兼容,再 Anthropic)。
# GLM(智谱)/ OpenAI 走 chat/completions;Anthropic 走 messages。可用 MBA_CLASSIFY_MODEL 覆盖模型。
def _env(name, default=""):
    """把未设 **和** 空串(CI 里未定义的 vars.* 会传空串)都当"未设",返回 default。"""
    return (os.environ.get(name) or default)


def _provider():
    m = _env("MBA_CLASSIFY_MODEL")
    if _env("GLM_API_KEY"):
        # 默认走智谱 **Anthropic 兼容端点**(/api/anthropic)—— 即 Claude Code 等交互式
        # 编码工具使用 GLM coding 套餐的方式。coding 套餐的 OpenAI /chat/completions 对
        # 程序化批量调用会 429 硬限流,Anthropic messages 端点则放行(模拟交互式工具)。
        # 想改用通用开放平台:GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
        #   + MBA_CLASSIFY_MODEL=glm-4-flash(base 含 paas → 自动切 openai 格式)。
        base = _env("GLM_BASE_URL", "https://open.bigmodel.cn/api/anthropic").rstrip("/")
        kind = "anthropic" if "anthropic" in base else "openai"
        return (kind, _env("GLM_API_KEY"), base, m or "glm-4.6")
    if _env("OPENAI_API_KEY"):
        return ("openai", _env("OPENAI_API_KEY"),
                _env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
                m or "gpt-4o-mini")
    if _env("ANTHROPIC_API_KEY"):
        return ("anthropic", _env("ANTHROPIC_API_KEY"),
                _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/"),
                m or "claude-haiku-4-5-20251001")
    return (None, None, None, None)

SYSTEM = (
    "你是 MBA 品牌舆情监测的分类助手。给你若干条**新闻标题**(逐字取自新闻源)。\n"
    "铁律:你**不得改写、翻译或编造**任何标题文字——只做分类判断,绝不生成新的事实文本。\n"
    "为每条严格输出一个 JSON 对象,字段:\n"
    "- keep(bool):是否值得作为品牌舆情**事件**入库。剔除:纯行情/涨跌榜/重复/软文/广告/\n"
    "  与该品牌无实质关系/纯个人观点评论/标题党无信息量。宁缺勿滥。\n"
    "- dim(str):从该条给出的 applicable_dims 里选**一个**最贴切(如 W5)。\n"
    "- severity(str):P0 重大 / P1 显著 / P2 一般 / P3 轻微。\n"
    "  **P0 判则(2026-07-25 加严)**:下列任一即 P0——\n"
    "  · 该品牌**旗舰产品 / 主力大模型的正式发布或重大版本更新**(对 AI 公司而言这是\n"
    "    最重要的事件类别之一;此前它常被判成 P1,导致「P0≥1 立即触发重审」这条规则失效);\n"
    "  · 监管处罚 / 禁令 / 判决或和解已下达;· 融资或并购完成且金额明确;\n"
    "  · 财报关键数字公布;· 大规模裁员或核心高管变动;· 重大安全事故 / 大规模服务中断。\n"
    "  输入里 `src` 为 `official` 表示该条**取自品牌官方新闻源**(一手公告,不是媒体转述)——\n"
    "  官方渠道发布的上述事件**优先判 P0**;但 `src` 只是来源标注,**不能**让招聘、\n"
    "  产品目录、状态页、技术博客这类日常内容因为「来自官网」就升级。\n"
    "- direction(str):pos/neg/neutral/mixed —— 这是**显式编辑判断**,不假装客观。\n"
    "- lens_map(数组):origin/category/leverage/identity/signal 的子集(1–3 个)。\n"
    "- confidence(str):high/med/low(你对这条分类的把握)。\n"
    "- reason(str):≤30 字中文理由。\n"
    "只输出一个 JSON 数组,与输入等长、顺序一致,不要任何额外文字或 markdown 围栏。"
)


def _clean(sug, applicable):
    """把模型返回规范化 + 兜底,保证字段合法(非法则留空/降级,由人工在 diff 里补)。"""
    out = {}
    out["keep"] = bool(sug.get("keep"))
    d = str(sug.get("dim", "")).strip().upper()
    out["dim"] = d if d in (applicable or DIMS) else ""
    s = str(sug.get("severity", "")).strip().upper()
    out["severity"] = s if s in SEVS else ""
    dr = str(sug.get("direction", "")).strip().lower()
    out["direction"] = dr if dr in DIRS else ""
    lm = sug.get("lens_map") or []
    if isinstance(lm, str):
        lm = [lm]
    out["lens_map"] = [x for x in lm if x in LENSES] or ["signal"]
    cf = str(sug.get("confidence", "")).strip().lower()
    out["confidence"] = cf if cf in ("high", "med", "low") else "low"
    out["reason"] = str(sug.get("reason", "")).strip()[:60]
    return out


def _extract_array(text):
    """稳健取 JSON 数组:忽略 ```围栏/前后散文,截取第一个 [ 到最后一个 ]。

    解析失败时给出**可诊断**的错误 —— 最常见的原因是 max_tokens 太小导致输出被截断
    (2026-07-25 实测踩过:17 家一次输出撞上 2000 上限,裸 JSONDecodeError 看不出病因)。
    """
    text = (text or "").strip()
    i, j = text.find("["), text.rfind("]")
    if i < 0 or j <= i:
        raise ValueError(f"模型返回无 JSON 数组(可能被截断或返回了散文):…{text[-160:]}")
    try:
        return json.loads(text[i:j + 1])
    except json.JSONDecodeError as e:
        raise ValueError(
            f"模型返回的 JSON 解析失败({e})。常见病因:**输出被 max_tokens 截断**"
            f"(本次返回 {len(text)} 字符);可减小批量或调大 max_tokens。尾部:…{text[-160:]}"
        ) from e


def call_llm(items, prov, system=None, max_tokens=2000, timeout=90):
    """items → 模型返回的 JSON 数组。按 provider 分派。

    `system` / `max_tokens` 可覆盖 —— 供别的预筛/分类脚本复用本函数的 provider 分派与
    429 退避逻辑,而**用自己的 prompt**。默认值保持本模块原行为不变。
    (2026-07-25:prescreen_reaudit 复用时没传 system,结果模型答的是「事件分类」而非
     「预筛」;且 17 家的输出撞上 max_tokens=2000 被截断 → JSONDecodeError。故开这两个口子。)
    """
    kind, key, base, model = prov
    sys_prompt = system or SYSTEM
    user = json.dumps(items, ensure_ascii=False)
    if kind == "anthropic":
        payload = {"model": model, "max_tokens": max_tokens, "system": sys_prompt,
                   "messages": [{"role": "user", "content": user}]}
        headers = {"content-type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": key}
        url = f"{base}/v1/messages"
    else:  # openai 兼容(GLM / OpenAI / 任意 OpenAI 兼容端点)
        payload = {"model": model, "max_tokens": max_tokens, "temperature": 0,
                   "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}]}
        headers = {"content-type": "application/json", "authorization": f"Bearer {key}"}
        url = f"{base}/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    # 429/5xx 退避重试(GLM coding 计划等端点 QPS 严,连发易被限流)。
    delays = [4, 10, 20, 35]
    for attempt in range(len(delays) + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < len(delays):
                ra = e.headers.get("Retry-After") if hasattr(e, "headers") else None
                wait = int(ra) if (ra and str(ra).isdigit()) else delays[attempt]
                print(f"classify: {e.code} 限流,{wait}s 后重试({attempt + 1}/{len(delays)})", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    if kind == "anthropic":
        text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
    else:
        text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
    return _extract_array(text)


def classify(cands, prov):
    """给每条候选加 suggest 字段(model-judged)。分批调用;某批失败则该批留空建议。"""
    for c in cands:
        c["suggest"] = None
    starts = list(range(0, len(cands), BATCH))
    for bi, start in enumerate(starts):
        if bi:
            time.sleep(float(_env("MBA_CLASSIFY_BATCH_PAUSE", "2")))  # 批间隔,避开端点 QPS 限流
        chunk = cands[start:start + BATCH]
        items = [{"i": i, "brand": c.get("brand") or c.get("slug"),
                  "title": c.get("quote") or c.get("title"),
                  # official = 该条来自品牌官方新闻源的 site: 召回(discover 标注),
                  # 用于 severity 分级——官方渠道的旗舰发布是 P0 级事件。
                  "src": c.get("source_type") or "media",
                  "applicable_dims": c.get("applicable_dims") or DIMS}
                 for i, c in enumerate(chunk)]
        try:
            sugs = call_llm(items, prov)
        except Exception as e:
            print(f"classify: ⚠️ 批 {bi} 调用失败({e}),该批留空建议。", file=sys.stderr)
            continue
        for c, sug in zip(chunk, sugs if isinstance(sugs, list) else []):
            if isinstance(sug, dict):
                c["suggest"] = _clean(sug, c.get("applicable_dims"))
    return cands


def to_adopt(cands):
    """高置信 keep → adopt 事件(带 slug,给 fold_adopt)。低置信/keep=false 不入。"""
    events, kept, dropped, review = [], [], [], []
    for c in cands:
        sg = c.get("suggest")
        if not sg:
            review.append((c, "无建议(分类失败)"))
            continue
        if not sg["keep"]:
            dropped.append((c, sg["reason"] or "模型判为不入库"))
            continue
        if sg["confidence"] == "low" or not sg["dim"] or not sg["severity"] or not sg["direction"]:
            review.append((c, f"低置信/字段不全({sg['reason']})"))
            continue
        events.append({
            "slug": c["slug"], "date": c.get("date", ""), "dim": sg["dim"],
            "severity": sg["severity"], "direction": sg["direction"], "direction_by": "model-judged",
            "title": c.get("title") or c.get("quote"), "quote": c.get("quote"), "quote_type": "title",
            "url": c["url"], "fetched_at": c.get("fetched_at", ""), "lens_map": sg["lens_map"],
            "source_type": c.get("source_type", "media"),
            "note": f"LLM 预分类建议({sg['confidence']}):{sg['reason']}。标题/日期/URL 取自源 feed,分类 model-judged,合并前人工复核。",
        })
        kept.append((c, sg))
    return events, kept, dropped, review


def write_report(path, kept, dropped, review):
    if not path:
        return
    L = [f"# 舆情候选 LLM 预分类报告", ""]
    L.append(f"**采纳建议(高置信,已写入 adopt):{len(kept)} 条**")
    for c, sg in kept:
        L.append(f"- ✅ `{c['slug']}` [{sg['dim']}/{sg['severity']}/{sg['direction']}] {c.get('quote','')[:44]} —— {sg['reason']}")
    L.append(f"\n**需人工确认(低置信/字段不全,未采纳):{len(review)} 条**")
    for c, why in review:
        L.append(f"- ⚠️ `{c['slug']}` {c.get('quote','')[:44]} —— {why}")
    L.append(f"\n**已丢弃(模型判为噪音/无关):{len(dropped)} 条**")
    for c, why in dropped:
        L.append(f"- ✗ `{c['slug']}` {c.get('quote','')[:40]} —— {why}")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", help="候选 JSON(discover 产出)")
    ap.add_argument("--adopt", help="输出 adopt 文件(高置信 keep 事件)")
    ap.add_argument("--report", help="输出分类报告 md(可选,PR 正文用)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()

    prov = _provider()
    kind, key = prov[0], prov[1]
    if not key:
        print("classify: 未设 GLM_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY —— 跳过自动分类"
              "(退回候选流,人工 triage)。")
        return 0
    print(f"classify: provider={kind} model={prov[3]}")
    if not args.inp or not os.path.exists(args.inp):
        print(f"classify: 输入不存在 {args.inp},跳过。")
        return 0
    doc = json.load(open(args.inp, encoding="utf-8"))
    cands = doc.get("candidates", []) if isinstance(doc, dict) else doc
    if not cands:
        print("classify: 无候选,跳过。")
        return 0
    cands = classify(cands, prov)
    events, kept, dropped, review = to_adopt(cands)
    write_report(args.report, kept, dropped, review)
    if args.adopt and events:
        os.makedirs(os.path.dirname(args.adopt) or ".", exist_ok=True)
        json.dump(events, open(args.adopt, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"classify: ✅ {len(kept)} 条采纳建议 → {args.adopt}(丢弃 {len(dropped)} · 待确认 {len(review)})")
    else:
        print(f"classify: 无高置信采纳建议(丢弃 {len(dropped)} · 待确认 {len(review)}),不写 adopt。")
    return 0


def _selftest():
    # mock:直接喂一批候选 + 一份模型返回,验证 _clean/to_adopt/report 落盘
    cands = [
        {"slug": "deepseek", "date": "2026-07-15", "quote": "DeepSeek估值超3500亿元",
         "title": "DeepSeek估值超3500亿元", "url": "https://x/1", "applicable_dims": ["W5", "W8"],
         "fetched_at": "t", "source_type": "finance",
         "suggest": None},
        {"slug": "nvidia", "date": "2026-07-16", "quote": "英伟达(NVDA)股票股价_实时行情",
         "title": "英伟达股票股价", "url": "https://x/2", "applicable_dims": ["W1"], "suggest": None},
    ]
    cands[0]["suggest"] = _clean({"keep": True, "dim": "W5", "severity": "P1", "direction": "pos",
                                  "lens_map": ["signal", "leverage"], "confidence": "high",
                                  "reason": "一级市场估值信号"}, ["W5", "W8"])
    cands[1]["suggest"] = _clean({"keep": False, "dim": "W1", "severity": "P3", "direction": "neutral",
                                  "lens_map": ["signal"], "confidence": "high", "reason": "纯行情页"}, ["W1"])
    events, kept, dropped, review = to_adopt(cands)
    assert len(events) == 1 and events[0]["slug"] == "deepseek", events
    assert events[0]["direction"] == "pos" and events[0]["dim"] == "W5"
    assert len(dropped) == 1 and dropped[0][0]["slug"] == "nvidia"
    # 非法字段兜底
    bad = _clean({"keep": True, "dim": "W99", "severity": "X", "direction": "up", "lens_map": ["nope"]}, ["W5"])
    assert bad["dim"] == "" and bad["severity"] == "" and bad["direction"] == "" and bad["lens_map"] == ["signal"]

    # ↓ 锁住 2026-07-25 的「官方源 + P0 判则」改动(见 docs/16 §9.6)↓
    # 起因:Anthropic 发 Opus 5,库里只进了中文媒体转述(标题主语是"中国模型内卷"),
    # 官方公告没进库;且旗舰模型发布被判 P1,而触发规则 R1 是 P0≥1 才立即触发。
    assert "旗舰产品" in SYSTEM and "大模型" in SYSTEM, "P0 判则必须点名旗舰产品/大模型发布"
    assert "official" in SYSTEM and "`src`" in SYSTEM, "prompt 必须解释 src=official 的含义"
    assert "不能" in SYSTEM and "招聘" in SYSTEM, "必须防住『来自官网就升级』(招聘/目录/状态页)"
    import inspect
    src_run = inspect.getsource(run) if "run" in dir() else open(__file__).read()
    assert '"src": c.get("source_type")' in src_run, "payload 必须把 source_type 传给模型"
    # adopt 事件是合法 YAML/JSON
    import tempfile
    p = tempfile.mktemp(suffix=".yaml")
    json.dump(events, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    import yaml
    assert yaml.safe_load(open(p))[0]["slug"] == "deepseek"
    os.remove(p)
    print("classify selftest: ✅ 通过(_clean 兜底 / to_adopt 分流 / adopt 合法)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
