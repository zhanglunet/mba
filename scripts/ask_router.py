#!/usr/bin/env python3
"""问答解析器（PRD-081/T2，trend #407）。

生成式问答的"分诊台"：输入用户中文问题 → 输出 8 个意图之一或 "unknown"。
只决定"这个问题该看哪张图"，不读 data/deck.json、不画图、不写文件、不调网络。

设计依据：docs/plans/2026-10-19-genui-matrix.md
  §2.1 意图明细表（8 个意图，英文 slug）
  §2.2 唯一归属判定规则（三层裁决 + 第 0 层写操作拦截）
  §2.3 各意图触发关键词
  §六  黄金问题集（自测用）

意图：
    total      查总分      当前综合评分快照（多少分、归一化、哪一版）
    compare    维度对比    维度之间比强弱、排座次
    radar      维度雷达    五个维度整体画像
    delta      版本变化    和上一版比，变了多少
    volume     声量趋势    近 7 天声量随时间怎么走
    sentiment  口碑        正负面占比
    events     热点事件    本品牌最近出了什么事
    rivals     竞品动态    竞品/对手在干什么

裁决（确定性：同一输入永远同一输出，无随机、无时间依赖）：
    第 0 层：含写操作动词或超纲数据词（股价/股票/市值/营收/预测）→ "unknown"
            （只读红线 + 诚实边界，路由层掐死）
    第 1 层：排他词优先（解决设计好的 4 对重叠）
    第 2 层：命中计数（短语 len>=4 计 2 分，单词计 1 分；同一关键词只计一次）
    第 3 层：固定优先级 rivals > events > delta > sentiment > volume > compare > radar > total
    全程无命中 → "unknown"

用法：
    echo "最近7天声量怎么样？" | python3 scripts/ask_router.py
    python3 scripts/ask_router.py --question "哪个维度最弱？"
    python3 scripts/ask_router.py --self-test    # 20 黄金问题 + 5 fallback，自检路由表

纯标准库，零依赖。
"""

import argparse
import sys

# 规范版本（PRD-098/T3 第一批 V1）：本文件意图目录（INTENTS/INTENT_CN）与
# 触发词表（TRIGGERS/WRITE_VERBS/OUT_OF_SCOPE/PAIRS/PRIORITY）的版本号。
# 不兼容变更（增删意图、改裁决层级）递增主版本；仅增补触发词等兼容变更
# 递增次版本。ask.html 内 JS 版为双实现，两边须同步演进、保持版本口径一致。
ROUTER_SPEC_VERSION = "1.0.0"

# 8 个意图（§2.1），顺序仅用于展示，裁决顺序见 PRIORITY
INTENTS = ("total", "compare", "radar", "delta",
           "volume", "sentiment", "events", "rivals")

INTENT_CN = {
    "total": "查总分", "compare": "维度对比", "radar": "维度雷达",
    "delta": "版本变化", "volume": "声量趋势", "sentiment": "口碑",
    "events": "热点事件", "rivals": "竞品动态",
}

# §2.3 触发词表（T2 照表实现；短语命中权重高于单词，见 _score）
TRIGGERS = {
    "total": ["总分", "综合评分", "多少分", "评分", "归一化", "健康度", "哪一版", "版本"],
    "compare": ["最强", "最弱", "最高", "最低", "排名", "排序", "排个序",
                "对比", "哪个维度", "谁高谁低"],
    "radar": ["雷达", "画像", "全貌", "整体", "分布", "五个维度", "维度情况"],
    "delta": ["上版", "上次", "上一版", "变化", "涨跌", "涨了", "跌了",
              "Δ", "δ", "delta", "对比上", "动了"],  # δ：Δ 经 .lower() 后的形态
    "volume": ["声量", "音量", "讨论量", "热度", "趋势", "走势", "曲线",
               "每天", "每日", "近7天", "7天"],
    "sentiment": ["正负面", "正面", "负面", "口碑", "好评", "差评",
                  "占比", "比例", "中性"],
    "events": ["热点", "大事", "事件", "新闻", "发生了什么", "新消息", "动态"],
    "rivals": ["竞品", "对手", "对标", "友商", "同行"],
}

# §2.2 第 0 层：写操作动词（注意"重新打分"要在"重审"前先列，子串包含关系下长词优先检查）
WRITE_VERBS = ["重新打分", "重审", "推送", "发送", "刷新", "修改", "删除", "告警"]

# §3.1 超纲数据词：deck.json 里没有的数据（股价/营收/预测类）→ 直接 unknown，
# 不给"看起来像答案"的东西。关键词命中了也不算数。
OUT_OF_SCOPE = ["股价", "股票", "市值", "营收", "预测"]

# §2.2 第 1 层：排他词（重叠对 → (A意图, B意图, A排他词, B排他词或None)）
# B排他词为 None 表示"否则 → B"（B 有触发词命中时才算）
PAIRS = [
    ("rivals", "events",
     ["竞品", "对手", "对标", "友商"], None),
    ("sentiment", "volume",
     ["正负面", "正面", "负面", "口碑", "好评", "差评", "占比", "比例"],
     ["趋势", "走势", "曲线", "每天", "每日", "近7天", "7天"]),
    ("compare", "radar",
     ["最强", "最弱", "最高", "最低", "排名", "排序", "排个序", "对比"],
     ["雷达", "画像", "全貌", "整体", "分布"]),
    ("delta", "total",
     ["上版", "上次", "上一版", "变化", "涨跌", "涨了", "跌了", "对比上"], None),
]

# §2.2 第 3 层：固定优先级（窄口径优先）
PRIORITY = ["rivals", "events", "delta", "sentiment",
            "volume", "compare", "radar", "total"]


def _normalize(question):
    """归一化：去空白（含全角空格）、转小写。保证"最近 7 天"能命中"7天"。"""
    q = (question or "").replace(" ", "").replace("　", "")
    q = q.replace("\t", "").replace("\n", "")
    return q.lower()


def _hits(q, intent):
    """该意图命中的触发词（去重，保序）。"""
    seen = []
    for kw in TRIGGERS[intent]:
        if kw in q and kw not in seen:
            seen.append(kw)
    return seen


def _score(q, intent):
    """第 2 层分数：短语（len>=4）计 2 分，单词计 1 分。"""
    return sum(2 if len(kw) >= 4 else 1 for kw in _hits(q, intent))


def _which_high(q):
    """'哪个…高'模式（§2.2 compare 排他词）：'哪个'+高/低/强/弱 → compare 排他命中。"""
    return "哪个" in q and any(c in q for c in ("高", "低", "强", "弱"))


def _layer1(q, has_hit):
    """第 1 层：排他词优先。返回命中的意图（去重保序，可能 0/1/多个）。"""
    winners = []
    for a, b, a_words, b_words in PAIRS:
        if not (has_hit[a] or has_hit[b]):
            continue  # 该对不活跃
        a_ex = any(w in q for w in a_words)
        if a == "compare" and _which_high(q):
            a_ex = True
        if a_ex:
            winners.append(a)
        elif b_words is not None:
            if any(w in q for w in b_words):
                winners.append(b)
            # 两侧都没中排他词 → 该对不裁决
        elif has_hit[b]:
            winners.append(b)  # "否则 → B"（B 有命中才算）
    seen = []
    for w in winners:
        if w not in seen:
            seen.append(w)
    return seen


def route(question):
    """输入中文问题 → 8 个意图 slug 之一或 "unknown"。纯函数，确定性。"""
    q = _normalize(question)
    if not q:
        return "unknown"
    # 第 0 层：写操作拦截 + 超纲数据拦截
    if any(v in q for v in WRITE_VERBS):
        return "unknown"
    if any(w in q for w in OUT_OF_SCOPE):
        return "unknown"
    has_hit = {i: bool(_hits(q, i)) for i in INTENTS}
    # 第 1 层：排他词优先
    winners = _layer1(q, has_hit)
    if len(winners) == 1:
        return winners[0]
    # 第 2 层：命中计数（多对冲突时只在胜出者里比；无胜出者在全部意图里比）
    cands = winners if winners else [i for i in INTENTS if has_hit[i]]
    if not cands:
        return "unknown"
    cands.sort(key=lambda i: (-_score(q, i), PRIORITY.index(i)))  # 第 3 层：固定优先级
    return cands[0]


def route_debug(question):
    """调试用：返回 (意图, {意图: 命中的触发词})。"""
    q = _normalize(question)
    matched = {i: _hits(q, i) for i in INTENTS if _hits(q, i)}
    return route(question), matched


# §六 黄金问题集（问题 → 期望意图）
GOLDEN = [
    ("综合评分多少？", "total"),
    ("deepseek 现在多少分？", "total"),
    ("归一化评分是多少？", "total"),
    ("哪个维度最弱？", "compare"),
    ("五个维度排个序", "compare"),
    ("五个维度整体什么样？", "radar"),
    ("画一下维度雷达", "radar"),
    ("和上版比变了多少？", "delta"),
    ("总分涨了还是跌了？", "delta"),
    ("哪个维度变化最大？", "delta"),
    ("最近 7 天声量怎么样？", "volume"),
    ("每天的讨论量画出来", "volume"),
    ("声量走势如何？", "volume"),
    ("正负面占比怎么样？", "sentiment"),
    ("负面多吗？", "sentiment"),
    ("最近有什么大事？", "events"),
    ("Top 热点事件有哪些？", "events"),
    ("竞品在干什么？", "rivals"),
    ("对手有什么新动作？", "rivals"),
    # §六 fallback 集（5 个，全部走 unknown）
    ("今天天气怎么样？", "unknown"),
    ("帮我把报告重审一下", "unknown"),
    ("把摘要发到飞书群", "unknown"),
    ("deepseek 股价多少？", "unknown"),
    ("明年品牌影响力会涨吗？", "unknown"),
]


def self_test():
    """跑 §六 25 题自检，打印路由表。返回 0=全过，1=有失败。"""
    print("== ask_router 自检（§六 25 题）==")
    print("%-28s %-10s %-10s %s" % ("问题", "期望", "实际", "结果"))
    failed = 0
    for question, expected in GOLDEN:
        got = route(question)
        ok = got == expected
        failed += not ok
        mark = "PASS" if ok else "FAIL"
        print("%-28s %-10s %-10s %s" % (question, expected, got, mark))
    print("== %d/%d 通过 ==" % (len(GOLDEN) - failed, len(GOLDEN)))
    # 确定性抽查：同一问题跑 3 次必须一致
    for question, _ in GOLDEN[:5]:
        assert len({route(question) for _ in range(3)}) == 1, "非确定性！"
    print("确定性抽查 OK（5 题 × 3 次一致）")
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="问答解析器（PRD-081/T2）：问题 → 意图")
    ap.add_argument("--question", "-q", default=None, help="要路由的问题")
    ap.add_argument("--self-test", action="store_true", help="跑 §六 25 题自检")
    ap.add_argument("--debug", action="store_true", help="同时打印命中的触发词")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    question = args.question
    if question is None:
        if sys.stdin.isatty():
            ap.print_help()
            return 2
        question = sys.stdin.read().strip()
    if args.debug:
        intent, matched = route_debug(question)
        print(intent)
        for i, kws in matched.items():
            print("  %s(%s): %s" % (i, INTENT_CN[i], "、".join(kws)))
    else:
        print(route(question))
    return 0


if __name__ == "__main__":
    sys.exit(main())
