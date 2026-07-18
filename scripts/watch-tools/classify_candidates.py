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
        # 默认走智谱 **coding 计划**端点(OpenAI 兼容,服务 glm-4.6 等)。
        # 通用免费档用 GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4 + MBA_CLASSIFY_MODEL=glm-4-flash 覆盖。
        return ("openai", _env("GLM_API_KEY"),
                _env("GLM_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4").rstrip("/"),
                m or "glm-4.6")
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
    """稳健取 JSON 数组:忽略 ```围栏/前后散文,截取第一个 [ 到最后一个 ]。"""
    text = (text or "").strip()
    i, j = text.find("["), text.rfind("]")
    if i < 0 or j <= i:
        raise ValueError(f"模型返回无 JSON 数组:{text[:120]}")
    return json.loads(text[i:j + 1])


def call_llm(items, prov):
    """items: [{i, brand, title, applicable_dims}] → 建议列表(等长)。按 provider 分派。"""
    kind, key, base, model = prov
    user = json.dumps(items, ensure_ascii=False)
    if kind == "anthropic":
        payload = {"model": model, "max_tokens": 2000, "system": SYSTEM,
                   "messages": [{"role": "user", "content": user}]}
        headers = {"content-type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": key}
        url = f"{base}/v1/messages"
    else:  # openai 兼容(GLM / OpenAI / 任意 OpenAI 兼容端点)
        payload = {"model": model, "max_tokens": 2000, "temperature": 0,
                   "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
        headers = {"content-type": "application/json", "authorization": f"Bearer {key}"}
        url = f"{base}/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        body = json.loads(r.read().decode("utf-8"))
    if kind == "anthropic":
        text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
    else:
        text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
    return _extract_array(text)


def classify(cands, prov):
    """给每条候选加 suggest 字段(model-judged)。分批调用;某批失败则该批留空建议。"""
    for c in cands:
        c["suggest"] = None
    for start in range(0, len(cands), BATCH):
        chunk = cands[start:start + BATCH]
        items = [{"i": i, "brand": c.get("brand") or c.get("slug"),
                  "title": c.get("quote") or c.get("title"),
                  "applicable_dims": c.get("applicable_dims") or DIMS}
                 for i, c in enumerate(chunk)]
        try:
            sugs = call_llm(items, prov)
        except Exception as e:
            print(f"classify: ⚠️ 批 {start//BATCH} 调用失败({e}),该批留空建议。", file=sys.stderr)
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
