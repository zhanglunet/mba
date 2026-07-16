#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_collab_dinners.py — 从 collabs/<a>--<b>.yaml 生成「创始人晚餐(品牌×品牌合作推演)」页
site/collabs/<a>--<b>.html + 索引/组合器 site/collabs/index.html。

概念:把两个品牌的创始人放到一张饭桌上,按 5 镜头逐"道菜"聊潜在合作。**⚠️ 假想对谈**:
双方发言均为 **AI 演绎**其公开记录在案的立场(与 MBA「人物评委 = AI 模拟真人视角」同源),
**非本人真实发言、非双方证实的真实合作**;合作点为基于两品牌真实属性的**假想推演**。
页面硬编码醒目 disclaimer 横幅 + 诚实盒(tensions)。

- 部署产物:site/build.sh 构建时调用;site/collabs/ 已 gitignore(同 founders/watch/starmap)。
- 复用 build_founder_pages 的 house-style 骨架(STYLE/MARK/FAVICON/5 镜头色/esc)。

用法:python3 scripts/build_collab_dinners.py                     → 生成全部(含首页亮点块)
      python3 scripts/build_collab_dinners.py asiainfo--zhipu    → 只生成指定 stem(仍刷新首页块)
      python3 scripts/build_collab_dinners.py --check-home       → 只校验首页亮点块无漂移(CI 门禁)

首页「创始人晚餐 · 亮点」块:把精选那场晚餐的一段亮点对话(气泡)+ 合作点嵌进 site/index.html
的 <!-- DINNER:START/END --> 之间(单一真源 = collabs/*.yaml,机制同 build_home_cards 的 REPORTS 块)。
"""
import glob
import os
import sys

try:
    import yaml
except ImportError:
    print("build_collab_dinners: 需要 PyYAML", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_founder_pages import STYLE, MARK, FAVICON, LENSES, LENS_CN, LENS_COLOR, esc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLLABS_DIR = os.path.join(ROOT, "collabs")
FOUNDERS_DIR = os.path.join(ROOT, "founders")
OUT_DIR = os.path.join(ROOT, "site", "collabs")
META = os.path.join(ROOT, "site", "reports-meta.yaml")
INDEX = os.path.join(ROOT, "site", "index.html")

# 首页「创始人晚餐 · 亮点」生成块的标记(与 build_home_cards 的 REPORTS 块同机制,防双源漂移)
HOME_START = "<!-- DINNER:START — 生成自 collabs/*.yaml(scripts/build_collab_dinners.py --check-home 守漂移)· 勿手改 -->"
HOME_END = "<!-- DINNER:END -->"

LENS_ORDER = [lid for lid, _, _ in LENSES]

# 晚餐专属 CSS(叠加在共享 STYLE 之上)
COLLAB_CSS = """
  .disclaimer { background:#fbeee6; border:1px solid #e6b89c; border-left:3px solid var(--accent);
    border-radius:6px; padding:11px 14px; margin:0 0 20px; font-size:12.5px; color:#7a3b1e; line-height:1.55; }
  .scene { font-size:14px; color:#33302b; background:var(--card); border:1px solid var(--hair);
    border-radius:6px; padding:12px 15px; margin:0 0 26px; font-style:italic; }
  .course { margin:0 0 26px; }
  .course h2 { display:flex; align-items:center; gap:8px; }
  .course h2 .ldot { width:10px; height:10px; border-radius:50%; display:inline-block; }
  .turns { display:flex; flex-direction:column; gap:10px; margin:0 0 12px; }
  .bubble { max-width:82%; border:1px solid var(--hair); border-radius:12px; padding:10px 14px; background:var(--card); }
  .bubble.a { align-self:flex-start; border-top-left-radius:3px; }
  .bubble.b { align-self:flex-end; border-top-right-radius:3px; background:#f6f3ec; }
  .bubble .who { font-size:12px; font-weight:800; margin-bottom:3px; }
  .bubble .who .brand { font-weight:600; color:var(--muted); margin-left:6px; font-size:11px; }
  .bubble .say { font-size:13.5px; line-height:1.6; color:#26231f; }
  .idea { border-left:3px solid var(--up); background:#eef6f0; border-radius:6px; padding:9px 13px; font-size:13px; }
  .idea b { color:var(--up); }
  .box { border:1px solid var(--hair); border-radius:6px; padding:13px 16px; margin:0 0 16px; }
  .box.take { border-left:3px solid var(--up); background:#eef6f0; }
  .box.tension { border-left:3px solid var(--accent); background:#fbeee6; }
  .box h2 { margin:0 0 8px; border:none; padding:0; }
  .box ul { margin:0; padding-left:20px; } .box li { font-size:13.5px; margin:0 0 6px; line-height:1.55; }
  .pair-head { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin:0 0 4px; }
  .pair-head .vs { font-size:20px; color:var(--muted); font-weight:300; }
  .who-chip { font-size:13px; }
  .who-chip b { font-size:16px; }
  .who-chip .r { color:var(--muted); font-size:11.5px; }
  /* 组合器 */
  .picker { display:flex; gap:10px; align-items:center; flex-wrap:wrap; background:var(--card);
    border:1px solid var(--hair); border-radius:8px; padding:14px 16px; margin:0 0 22px; }
  .picker select { font:inherit; font-size:13.5px; padding:6px 10px; border:1px solid var(--hair); border-radius:6px; background:#fff; }
  .picker .vs { color:var(--muted); }
  .picker #go { font:inherit; font-weight:700; font-size:13.5px; padding:6px 14px; border-radius:6px;
    border:1px solid var(--accent); background:var(--accent); color:#fff; text-decoration:none; cursor:pointer; }
  .picker #go.disabled { background:#fff; color:var(--muted); border-color:var(--hair); cursor:default; }
  .picker #order { font:inherit; font-weight:700; font-size:13.5px; padding:6px 14px; border-radius:6px;
    border:1px solid var(--accent); background:#fff; color:var(--accent); text-decoration:none; cursor:pointer; }
  .picker #hint { font-size:12.5px; color:var(--muted); }
  .picker .hidden { display:none; }
  .dgrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:12px; }
  .dcard { display:block; background:var(--card); border:1px solid var(--hair); border-radius:6px;
    padding:14px 16px; text-decoration:none; color:var(--ink); }
  .dcard:hover { border-color:var(--accent); }
  .dcard .t { font-size:14.5px; font-weight:800; line-height:1.35; }
  .dcard .p { font-size:12.5px; color:var(--muted); margin-top:5px; }
"""

DISCLAIMER = ("🍽️ <b>假想晚餐</b> · 双方发言为 <b>AI 演绎</b>其公开记录在案的立场"
              "(与 MBA「人物评委」同一机制)· <b>非本人真实发言</b> · "
              "<b>非双方证实的真实合作</b> · 合作点为基于两品牌真实属性的假想推演,仅作调研启发。")


def load_yaml(path):
    return yaml.safe_load(open(path, encoding="utf-8")) or {}


def founder_info(slug):
    """返回 (name_cn, role)。缺文件时回落 slug。"""
    p = os.path.join(FOUNDERS_DIR, f"{slug}.yaml")
    if not os.path.exists(p):
        return slug, ""
    f = (load_yaml(p).get("founder") or {})
    return f.get("name_cn", slug), f.get("role", "")


def brand_names():
    out = {}
    for r in (load_yaml(META).get("reports") or []):
        out[r["slug"]] = r.get("brand_cn") or r.get("card_brand") or r["slug"]
    return out


def shell(title, desc, nav_html, body):
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}" />
<style>{STYLE}{COLLAB_CSS}</style>
{FAVICON}
</head>
<body>
<div class="wrap">
  <header>
    {MARK}
    <nav>{nav_html}</nav>
  </header>
{body}
  <footer>
    创始人晚餐是<strong>假想推演</strong>:双方发言为 AI 演绎其公开立场(非本人真实发言),合作点为
    基于两品牌真实属性的假想机会(非双方证实的真实合作),诚实盒同时列出合作张力。<strong>只作调研启发,不改评分</strong>。
    © 2026 MBA · Jason · 清风 · John · 技术支持 <a href="https://marsdata.ai" style="color:var(--ink);">marsdata.ai</a>
  </footer>
</div>
</body>
</html>
"""


def render_dinner(stem, data, names):
    a, b = data["brands"]                       # 已按字母序(校验器保证 stem==canonical)
    an, ar = founder_info(a)
    bn, br = founder_info(b)
    abn = {a: (an, names.get(a, a)), b: (bn, names.get(b, b))}

    courses = sorted(data.get("courses") or [],
                     key=lambda c: LENS_ORDER.index(c["lens"]) if c.get("lens") in LENS_ORDER else 99)
    course_html = []
    for c in courses:
        lid = c.get("lens")
        color = LENS_COLOR.get(lid, "#8a857c")
        bubbles = []
        for t in (c.get("exchange") or []):
            who = t.get("who")
            side = "a" if who == a else "b"
            nm, brand = abn.get(who, (who, who))
            bubbles.append(
                f'<div class="bubble {side}"><div class="who">{esc(nm)}'
                f'<span class="brand">{esc(brand)}</span></div>'
                f'<div class="say">{esc(t.get("say"))}</div></div>')
        course_html.append(f"""  <div class="course">
    <h2><span class="ldot" style="background:{color}"></span>{esc(LENS_CN.get(lid, lid))}</h2>
    <div class="turns">
      {"".join(bubbles)}
    </div>
    <div class="idea"><b>合作点(假想):</b> {esc(c.get("idea"))}</div>
  </div>""")

    takeaways = "".join(f"<li>{esc(x)}</li>" for x in (data.get("takeaways") or []))
    tensions = "".join(f"<li>{esc(x)}</li>" for x in (data.get("tensions") or []))
    sources = "".join(f"<li>{esc(x)}</li>" for x in (data.get("sources") or []))

    def xlinks(slug, nm, brand):
        return (f'<a href="/founders/{esc(slug)}.html">{esc(nm)} 创始人页 →</a>'
                f'<a href="/reports/{esc(slug)}/" style="margin-left:14px">{esc(brand)} 报告 →</a>')

    body = f"""
  <p class="disclaimer">{DISCLAIMER}</p>
  <div class="pair-head">
    <span class="who-chip"><b>{esc(an)}</b><br><span class="r">{esc(names.get(a, a))} · {esc(ar)}</span></span>
    <span class="vs">×</span>
    <span class="who-chip"><b>{esc(bn)}</b><br><span class="r">{esc(names.get(b, b))} · {esc(br)}</span></span>
  </div>
  <h1 style="margin-top:8px">{esc(data.get("title"))}</h1>
  <p class="scene">{esc(data.get("scene"))}</p>

{"".join(course_html)}

  <div class="box take"><h2>假想合作备忘</h2><ul>{takeaways}</ul></div>
  <div class="box tension"><h2>合作张力(诚实盒)</h2><ul>{tensions}</ul></div>

  <div class="xlinks" style="margin-top:6px">{xlinks(a, an, names.get(a, a))}</div>
  <div class="xlinks" style="margin-top:4px">{xlinks(b, bn, names.get(b, b))}</div>

  <h2>数据来源(可复盘)</h2>
  <ul class="sources">{sources}</ul>
"""
    nav = ('<a href="/">品牌监控</a>'
           '<a href="/founders/">创始人</a>'
           '<a href="/collabs/" aria-current="page">创始人晚餐</a>'
           '<a href="/watch/">舆情信号</a>'
           '<a href="/panorama.html">评委全景</a>')
    title = f"{an} × {bn} · 创始人晚餐 · MBA"
    desc = f"{an}（{names.get(a, a)}）× {bn}（{names.get(b, b)}）的假想晚餐:按 5 镜头推演潜在合作(AI 演绎·非真实合作)。"
    return shell(title, desc, nav, body)


def render_index(built, names):
    """built: [(stem, [a,b], title)]。索引 + 组合器。"""
    import json
    # 组合器需要的创始人清单(有 founders/*.yaml 的品牌)
    founders = []
    for p in sorted(glob.glob(os.path.join(FOUNDERS_DIR, "*.yaml"))):
        slug = os.path.splitext(os.path.basename(p))[0]
        nm, _ = founder_info(slug)
        founders.append({"slug": slug, "name": nm, "brand": names.get(slug, slug)})
    built_stems = [s for s, _, _ in built]

    opts = "".join(f'<option value="{esc(f["slug"])}">{esc(f["name"])}（{esc(f["brand"])}）</option>'
                   for f in founders)
    cards = "".join(
        f'<a class="dcard" href="/collabs/{esc(stem)}.html"><div class="t">{esc(title)}</div>'
        f'<div class="p">{esc(founder_info(br[0])[0])} × {esc(founder_info(br[1])[0])}</div></a>'
        for stem, br, title in built)

    data_json = json.dumps({"built": built_stems, "founders": founders}, ensure_ascii=False)
    body = f"""
  <h1>创始人晚餐 · Founder Dinners</h1>
  <p class="lede">把两个品牌的创始人放到一张饭桌上,按 5 镜头逐"道菜"聊潜在合作。
    <strong>假想推演</strong>:发言为 AI 演绎公开立场、合作为假想机会,并列出诚实的合作张力。<strong>只作调研启发,不改评分。</strong></p>

  <div class="picker">
    <select id="fa"><option value="">选创始人 A</option>{opts}</select>
    <span class="vs">×</span>
    <select id="fb"><option value="">选创始人 B</option>{opts}</select>
    <a id="go" class="hidden" href="#">开饭 →</a>
    <a id="order" class="hidden" target="_blank" rel="noopener" href="#">🍽️ 点单让我加这场 →</a>
    <span id="hint"></span>
  </div>

  <h2>已上桌的晚餐</h2>
  <div class="dgrid">{cards}</div>

  <script>
  (function(){{
    var D = {data_json};
    var REPO = 'https://github.com/zhanglunet/mba';
    var byId = {{}}; D.founders.forEach(function(f){{ byId[f.slug]=f; }});
    var fa=document.getElementById('fa'), fb=document.getElementById('fb'),
        go=document.getElementById('go'), order=document.getElementById('order'), hint=document.getElementById('hint');
    function show(el,on){{ el.className = on ? '' : 'hidden'; }}
    function orderUrl(a,b,stem){{
      var ma=byId[a]||{{name:a,brand:a,slug:a}}, mb=byId[b]||{{name:b,brand:b,slug:b}};
      var title='创始人晚餐点单：'+ma.name+'（'+ma.brand+'） × '+mb.name+'（'+mb.brand+'）';
      var body='请为这两位创始人加一场假想晚餐(品牌×品牌合作推演):\\n\\n'
             +'- '+ma.name+' — '+ma.brand+'（'+ma.slug+'）\\n'
             +'- '+mb.name+' — '+mb.brand+'（'+mb.slug+'）\\n\\n'
             +'slug 对：'+stem+'\\n\\n(由 mbabrand.com/collabs/ 组合器点单生成)';
      return REPO+'/issues/new?title='+encodeURIComponent(title)+'&body='+encodeURIComponent(body);
    }}
    function upd(){{
      var a=fa.value,b=fb.value;
      show(go,false); show(order,false);
      if(!a||!b){{ hint.textContent=''; return; }}
      if(a===b){{ hint.textContent='请选两位不同的创始人'; return; }}
      var stem=[a,b].sort().join('--');
      if(D.built.indexOf(stem)>=0){{ go.href='/collabs/'+stem+'.html'; show(go,true); hint.textContent=''; }}
      else {{ order.href=orderUrl(a,b,stem); show(order,true); hint.textContent='这桌还没上 —— 点单开一张 GitHub issue,我看到就加'; }}
    }}
    fa.addEventListener('change',upd); fb.addEventListener('change',upd);
  }})();
  </script>
"""
    nav = ('<a href="/">品牌监控</a>'
           '<a href="/founders/">创始人</a>'
           '<a href="/collabs/" aria-current="page">创始人晚餐</a>'
           '<a href="/watch/">舆情信号</a>'
           '<a href="/starmap.html">知识星图</a>'
           '<a href="/docs.html">文档</a>')
    return shell("创始人晚餐 · Founder Dinners · MBA",
                 "MBA 创始人晚餐:把两个品牌的创始人放到一桌,按 5 镜头假想推演潜在合作(AI 演绎·非真实合作)。",
                 nav, body)


import re as _re  # noqa: E402

_CJK = "‘’“”　-〿㐀-䶿一-鿿＀-￯"
_CJK_SPACE = _re.compile(f"(?<=[{_CJK}]) (?=[{_CJK}])")


def _collapse(s):
    """折叠 YAML 折叠标量(`>-`)里残留的多余空白;并去掉 CJK 字符间的折行空格
    (与 build_home_cards.collapse_ws 同口径),让首页 teaser 里的中文不带断行空隙。"""
    s = " ".join((s or "").split())
    return _CJK_SPACE.sub("", s)


def pick_featured(collabs):
    """从全部晚餐里选首页精选那场。规则(确定性):
       优先 featured==True 的第一场(按 stem 字母序),否则第一场(字母序)。
       collabs: [(stem, data)],已按 stem 排序。返回 (stem, data) 或 None。"""
    if not collabs:
        return None
    for stem, data in collabs:
        if data.get("featured") is True:
            return stem, data
    return collabs[0]


def pick_highlight_course(data):
    """选亮点那道菜:home_highlight 指定的 lens,否则第一道(按 5 镜头序)。"""
    courses = sorted(data.get("courses") or [],
                     key=lambda c: LENS_ORDER.index(c["lens"]) if c.get("lens") in LENS_ORDER else 99)
    if not courses:
        return None
    hl = data.get("home_highlight")
    if hl:
        for c in courses:
            if c.get("lens") == hl:
                return c
    return courses[0]


def render_home_block(collabs, names):
    """生成首页 <!-- DINNER:START/END --> 之间的「创始人晚餐 · 亮点」块。
       collabs: [(stem, data)] 已按 stem 排序。无晚餐时给一句去组合器的兜底。
       样式类(.dh-*)手写在 site/index.html 的 <style> 头,本函数只吐结构 HTML。"""
    total = len(collabs)
    more = (f'<a class="dh-more" href="/collabs/">组合更多创始人 · 共 {total} 场 →</a>'
            if total else '<a class="dh-more" href="/collabs/">去组合器 →</a>')
    if not collabs:
        return ('      <div class="dinner-hl">\n'
                '        <div class="dh-head"><h2>🍽️ 创始人晚餐 · 亮点</h2>'
                f'{more}</div>\n'
                '        <p class="dh-empty">把两个品牌的创始人放到一桌,按 5 镜头假想推演潜在合作。'
                '<a href="/collabs/">去组合器点单 →</a></p>\n'
                '      </div>')

    feat = pick_featured(collabs)
    stem, data = feat
    a, b = data["brands"]
    an, ar = founder_info(a)
    bn, br = founder_info(b)
    course = pick_highlight_course(data)

    bubbles = ""
    if course:
        for t in (course.get("exchange") or []):
            who = t.get("who")
            side = "a" if who == a else "b"
            nm = an if who == a else bn
            brand = names.get(who, who)
            bubbles += (f'<div class="dh-bubble {side}"><div class="dh-who">{esc(nm)}'
                        f'<span class="brand">{esc(brand)}</span></div>'
                        f'<div class="dh-say">{esc(_collapse(t.get("say")))}</div></div>')
        lens_cn = LENS_CN.get(course.get("lens"), course.get("lens"))
        lens_color = LENS_COLOR.get(course.get("lens"), "#8a857c")
        idea = (f'<div class="dh-idea"><b>合作点(假想):</b> {esc(_collapse(course.get("idea")))}</div>'
                if course.get("idea") else "")
    else:
        lens_cn, lens_color, idea = "", "#8a857c", ""

    return f"""      <div class="dinner-hl">
        <div class="dh-head"><h2>🍽️ 创始人晚餐 · 亮点</h2>{more}</div>
        <div class="dh-card">
          <div class="dh-pair"><b>{esc(an)}</b><span class="r">{esc(names.get(a, a))}</span>
            <span class="vs">×</span><b>{esc(bn)}</b><span class="r">{esc(names.get(b, b))}</span>
            <span class="dh-lens" style="border-color:{lens_color};color:{lens_color}">{esc(lens_cn)}</span></div>
          <div class="dh-title">{esc(data.get("title"))}</div>
          <div class="dh-turns">{bubbles}</div>
          {idea}
          <div class="dh-foot">
            <span class="dh-disc">🍽️ 假想对谈 · 双方发言为 <b>AI 演绎</b>其公开立场 · 非本人真实发言 · 非双方证实的真实合作</span>
            <span class="dh-cta"><a href="/collabs/{esc(stem)}.html">看这场完整晚餐(5 镜头)→</a></span>
          </div>
        </div>
      </div>"""


def splice_home(index_text, block):
    if HOME_START not in index_text or HOME_END not in index_text:
        raise SystemExit(
            f"build_collab_dinners: index.html 缺少标记 {HOME_START!r} / {HOME_END!r}(请先手动加一次)")
    pre, rest = index_text.split(HOME_START, 1)
    _, post = rest.split(HOME_END, 1)
    return f"{pre}{HOME_START}\n{block}\n      {HOME_END}{post}"


def collect_collabs():
    out = []
    for path in sorted(glob.glob(os.path.join(COLLABS_DIR, "*.yaml"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        out.append((stem, load_yaml(path)))
    return out


def home_main(check):
    """写(或 --check-home 校验)首页「创始人晚餐 · 亮点」块。与 collab 页生成解耦,
       让 check_consistency 能单独跑漂移门禁。"""
    if not os.path.exists(INDEX):
        print("build_collab_dinners --home: site/index.html 不存在(跳过)。")
        return 0
    names = brand_names()
    block = render_home_block(collect_collabs(), names)
    cur = open(INDEX, encoding="utf-8").read()
    new = splice_home(cur, block)
    if check:
        if new != cur:
            print("❌ 首页「创始人晚餐 · 亮点」块与 collabs/*.yaml 漂移 —— "
                  "跑 `python3 scripts/build_collab_dinners.py` 重生成。")
            cl, nl = cur.splitlines(), new.splitlines()
            for i in range(min(len(cl), len(nl))):
                if cl[i] != nl[i]:
                    print(f"   首个差异 @ 行 {i+1}:\n     - 现有: {cl[i].strip()[:100]}\n     + 应为: {nl[i].strip()[:100]}")
                    break
            return 1
        print("✅ 首页「创始人晚餐 · 亮点」块与 collabs/*.yaml 同步(无漂移)。")
        return 0
    open(INDEX, "w", encoding="utf-8").write(new)
    print("[collab-dinners] 已重写 site/index.html 的「创始人晚餐 · 亮点」块。")
    return 0


def main(argv):
    if "--check-home" in argv:
        return home_main(check=True)
    if not os.path.isdir(COLLABS_DIR):
        print("build_collab_dinners: collabs/ 不存在 —— 跳过。")
        return 0
    only = argv[0] if argv else None
    names = brand_names()
    os.makedirs(OUT_DIR, exist_ok=True)
    built = []
    n = 0
    for path in sorted(glob.glob(os.path.join(COLLABS_DIR, "*.yaml"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        data = load_yaml(path)
        brands = data.get("brands") or []
        title = data.get("title", stem)
        built.append((stem, brands, title))
        if only and stem != only:
            continue
        with open(os.path.join(OUT_DIR, f"{stem}.html"), "w", encoding="utf-8") as fh:
            fh.write(render_dinner(stem, data, names))
        print(f"[collab-dinners] site/collabs/{stem}.html")
        n += 1

    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_index(built, names))
    print(f"[collab-dinners] site/collabs/index.html({len(built)} 场晚餐)")
    # 首页「创始人晚餐 · 亮点」块(index.html 是版本受控文件,随构建刷新;漂移由 check_consistency 兜)
    home_main(check=False)
    print(f"[collab-dinners] done — {n} dinner page(s) + index + 首页亮点块")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
