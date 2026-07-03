#!/usr/bin/env python3
"""Build mbabrand.com 的 agent-facing 静态 JSON 端点。

读这些源:
  - site/published-reports.txt   发布白名单
  - site/reports-meta.yaml       已发布报告的元数据
  - metric-brand-auditor/panels/*.yaml    评委 panel 配置
  - metric-brand-auditor/panels/industries.yaml  行业 → panel 映射
  - perspectives/*-perspective/SKILL.md   评委身份 (front matter)
  - metric-brand-auditor/references/dimensions.md   7 维度
  - metric-brand-auditor/references/judge-prompt-template.md   5 镜头

写出 site/api/*.json,供 agent 通过 HTTP 直接拉。

被 site/build.sh 在 Cloudflare Pages build step 调用,本地 dev 可独立跑:

    python3 scripts/build_agents_api.py
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml

ROOT          = Path(__file__).resolve().parent.parent
SITE_DIR      = ROOT / "site"
API_DIR       = SITE_DIR / "api"
WHITELIST     = SITE_DIR / "published-reports.txt"
REPORTS_META  = SITE_DIR / "reports-meta.yaml"
PANELS_DIR    = ROOT / "metric-brand-auditor" / "panels"
REFS_DIR      = ROOT / "metric-brand-auditor" / "references"
PERSP_DIR     = ROOT / "perspectives"


# -------------------------------------------------------------- helpers ----

# When True, write_json() compares the generated content against the committed
# file instead of writing — used by the CI drift guard (`--check`). The only
# volatile field is index.json's generated_at, which _normalize() masks so the
# comparison is stable across runs.
CHECK_MODE = False
_PRODUCED: set[str] = set()
DRIFT: list[str] = []


def _normalize(rel_path: str, text: str) -> str:
    if rel_path == "index.json":
        text = re.sub(r'("generated_at":\s*)"[^"]*"', r'\1"<ignored>"', text)
    return text


def write_json(rel_path: str, data) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    out = API_DIR / rel_path
    if CHECK_MODE:
        _PRODUCED.add(rel_path)
        if not out.exists():
            DRIFT.append(f"missing: api/{rel_path} (generator produces it, repo doesn't have it)")
        elif _normalize(rel_path, out.read_text(encoding="utf-8")) != _normalize(rel_path, text):
            DRIFT.append(f"drift:   api/{rel_path}")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"[agents-api] wrote /api/{rel_path}")


def write_text_file(out: Path, text: str, label: str) -> None:
    """Like write_json but for a raw text artifact outside api/ (e.g. llms.txt).
    Participates in --check (exact compare; no volatile fields)."""
    if CHECK_MODE:
        if not out.exists():
            DRIFT.append(f"missing: {label} (generator produces it, repo doesn't have it)")
        elif out.read_text(encoding="utf-8") != text:
            DRIFT.append(f"drift:   {label}")
        return
    out.write_text(text, encoding="utf-8")
    print(f"[agents-api] wrote {label}")


def read_whitelist() -> list[str]:
    slugs = []
    for line in WHITELIST.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        slugs.append(t)
    return slugs


def parse_skill_front_matter(path: Path) -> dict:
    """SKILL.md 顶部用 --- ... --- 包 YAML front matter。"""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def first_paragraph(text: str) -> str:
    """取 description 第一段(到第一个空行或换行 + 中文标点结束)。"""
    if not text:
        return ""
    para = text.strip().split("\n\n")[0]
    para = " ".join(line.strip() for line in para.splitlines())
    return para.strip()


# ----------------------------------------------------------- judges build ---

def build_judges() -> tuple[list[dict], dict[str, dict]]:
    """Returns (list_items, by_slug_body)."""
    items = []
    bodies = {}
    for path in sorted(PERSP_DIR.glob("*-perspective/SKILL.md")):
        fm = parse_skill_front_matter(path)
        full_name = fm.get("name", path.parent.name)
        slug = full_name.replace("-perspective", "")
        desc = (fm.get("description") or "").strip()
        items.append({
            "slug": slug,
            "name": full_name,
            "summary": first_paragraph(desc),
            "skill_url": f"https://github.com/zhanglunet/mba/blob/main/perspectives/{path.parent.name}/SKILL.md",
            "api_url": f"/api/judges/{slug}.json",
        })
        bodies[slug] = {
            "slug": slug,
            "name": full_name,
            "description": desc,
            "skill_url": f"https://github.com/zhanglunet/mba/blob/main/perspectives/{path.parent.name}/SKILL.md",
        }
    return items, bodies


# ----------------------------------------------------------- panels build ---

def build_panels(judges_by_slug: dict[str, dict]) -> tuple[list[dict], dict[str, dict], dict]:
    """Returns (list_items, by_slug_full, industries_map)."""
    items = []
    bodies = {}
    industries: dict = {}
    for path in sorted(PANELS_DIR.glob("*.yaml")):
        name = path.stem
        with path.open(encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        if name == "industries":
            industries = data
            continue
        if "judges" not in data:
            continue
        judges = data.get("judges") or []
        items.append({
            "slug": data.get("name", name),
            "display_name": data.get("display_name", name),
            "status": data.get("status", "production"),
            "judges_count": len(judges),
            "description": first_paragraph(data.get("description", "")),
            "api_url": f"/api/panels/{data.get('name', name)}.json",
        })
        bodies[data.get("name", name)] = {
            "slug": data.get("name", name),
            "display_name": data.get("display_name", name),
            "status": data.get("status", "production"),
            "description": (data.get("description") or "").strip(),
            "judges": [
                {
                    "slug": j.get("slug"),
                    "display_name_cn": j.get("display_name_cn"),
                    "display_name_en": j.get("display_name_en"),
                    "language": j.get("language"),
                    "weight": j.get("weight", 1.0),
                    "api_url": f"/api/judges/{j.get('slug')}.json"
                    if j.get("slug") in judges_by_slug else None,
                }
                for j in judges
            ],
        }
    return items, bodies, industries


# -------------------------------------------------------- methodology build -

def build_methodology() -> dict:
    dim_md = (REFS_DIR / "dimensions.md").read_text(encoding="utf-8")
    dim_rows = re.findall(r"^## (\d+)\.\s+(.+?)(?:\s+\(.*?\))?$", dim_md, flags=re.MULTILINE)
    dimensions = []
    for n, name in dim_rows:
        n = int(n)
        # slug = lowercase-hyphenated, EN only
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        dimensions.append({
            "n": n,
            "slug": slug,
            "name_en": name,
            "tier": "core" if n <= 7 else "advanced",
        })

    judge_md = (REFS_DIR / "judge-prompt-template.md").read_text(encoding="utf-8")
    lens_rows = re.findall(r"^  (\d)\.\s+([A-Z][A-Za-z\- ]+?)\s+—\s+(.+)$", judge_md, flags=re.MULTILINE)
    lenses = []
    for n, name, desc in lens_rows[:5]:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        lenses.append({
            "n": int(n),
            "slug": slug,
            "name_en": name.strip(),
            "description": desc.strip(),
        })

    pipeline = [
        {"phase": 0, "name": "Router", "summary": "Lead checks reports/<brand>/report.md → FRESH or EVOLUTION."},
        {"phase": 1, "name": "Discovery", "summary": "Lead drafts PRD: brand framing, 7 dimensions, panel choice, optional cloud-browser leg."},
        {"phase": 2, "name": "Parallel Search", "summary": "N sub-agents research one dimension each + optional Wuying cloud-browser leg."},
        {"phase": 3, "name": "Synthesis", "summary": "Lead reads _raw/ → synthesis.md: leverage map, fragile edges, cross-dim contradictions."},
        {"phase": 4, "name": "N-Judge Panel", "summary": "Each judge loads its perspective skill, scores 5 lenses 1-10 independently."},
        {"phase": 5, "name": "Lead Merge", "summary": "Synthesis + reviews → report.md / report.html / versions/v{n}."},
    ]
    return {
        "framework": {
            "dimensions_total": len(dimensions),
            "dimensions_default": sum(1 for d in dimensions if d["tier"] == "core"),
            "lenses_total": len(lenses),
            "judges_default": 5,
        },
        "dimensions": dimensions,
        "lenses": lenses,
        "pipeline": pipeline,
        "panel_resolution_order": [
            "--panel <name>          # CLI flag",
            "--industry <name>       # industries.yaml map",
            "reports/<brand>/panel.yaml  # brand-bound panel",
            "panels/default.yaml     # fallback",
        ],
    }


# ----------------------------------------------------------- reports build --

def build_reports() -> tuple[list[dict], dict[str, dict]]:
    slugs = read_whitelist()
    meta = yaml.safe_load(REPORTS_META.read_text(encoding="utf-8")) or {}
    meta_by_slug = {r["slug"]: r for r in (meta.get("reports") or [])}

    items = []
    bodies = {}
    for slug in slugs:
        m = meta_by_slug.get(slug)
        if not m:
            msg = f"{slug} listed in published-reports.txt but missing in reports-meta.yaml"
            if CHECK_MODE:
                DRIFT.append(f"meta:    {msg}")
            else:
                print(f"[agents-api] WARN: {msg} — skipping", file=sys.stderr)
            continue
        common = {
            "slug": slug,
            "brand_cn": m.get("brand_cn"),
            "brand_en": m.get("brand_en"),
            "ticker": m.get("ticker"),
            "version": m.get("version"),
            "audit_date": m.get("audit_date").isoformat() if isinstance(m.get("audit_date"), datetime.date) else m.get("audit_date"),
            "panel": m.get("panel"),
            "score": {
                "total": m.get("score_total"),
                "max": m.get("score_max"),
                "normalized": m.get("score_normalized"),
            },
            "tl_dr": m.get("tl_dr"),
            "html_url": f"/reports/{slug}/",
            "pdf_url": f"/reports/{slug}/report.pdf" if m.get("has_pdf") else None,
            "api_url": f"/api/reports/{slug}.json",
        }
        items.append(common)
        bodies[slug] = {**common, "panel_api_url": f"/api/panels/{m.get('panel')}.json"}
    return items, bodies


# ----------------------------------------------------------- static blobs --

def build_about() -> dict:
    return {
        "name": "MBA — Metric Brand Auditor",
        "tagline": "Brand judgment for the agentic age — scored, versioned, replayable.",
        "tagline_cn": "AI 时代的品牌影响力审计协议:多智能体并行调研 + N 评委独立打分 + 版本化报告。",
        "what_it_is": [
            "Lead-orchestrated multi-agent pipeline that audits a brand across 7 default dimensions × 5 lenses.",
            "Each audit is one HTML + Markdown report frozen to /versions/v{n}, snapshotting the brand at that date.",
            "Evolution mode re-runs only changed dimensions and bumps the version.",
        ],
        "team": ["Jason", "清风", "John"],
        "stack": ["Claude Opus 4.7", "Claude Code skills", "Static-first publishing"],
        "site": "https://mbabrand.com",
        "repo": "https://github.com/zhanglunet/mba",
        "install": "https://www.botlearn.ai/en/community/u/mba_auditor",
        "license": "Apache-2.0",
        "disclaimer": "Hackathon demo. Judge avatars / scores / verdicts are AI simulations of public personas — not the real people's opinions. Reports do not constitute investment advice.",
    }


def build_install() -> dict:
    return {
        "skill_invoke": "/mba <brand>",
        "quick_start": [
            "/mba openai --quick --no-judges    # single-pass open-web read, no judge panel",
            "/mba lenovo                        # full pipeline, default 5-judge panel",
            "/mba xpeng --panel auto            # use a specific industry panel",
            "/mba <brand> --refresh             # force EVOLUTION even if report exists",
        ],
        "platforms": [
            {
                "name": "BotLearn (SkillHunt)",
                "url": "https://www.botlearn.ai/en/community/u/mba_auditor",
                "description": "One-click install into Claude Code as a skill named `mba_auditor`.",
            },
            {
                "name": "GitHub (manual)",
                "url": "https://github.com/zhanglunet/mba",
                "description": "Clone the repo and point Claude Code's skills directory at metric-brand-auditor/ + perspectives/.",
            },
            {
                "name": "MCP server (npx)",
                "package": "mba-mcp-server",
                "description": "Run audits from Claude Desktop, Cursor, or any MCP-capable agent. Requires ANTHROPIC_API_KEY.",
                "config_example": {
                    "mcpServers": {
                        "mba": {
                            "command": "npx",
                            "args": ["-y", "mba-mcp-server@latest"],
                            "env": {"ANTHROPIC_API_KEY": "sk-ant-..."},
                        }
                    }
                },
                "tools": [
                    "propose_audit",
                    "confirm_audit",
                    "get_status",
                    "fetch_report",
                    "list_audits",
                    "add_judge",
                    "subscribe_brand",
                    "trigger_evolution",
                    "list_subscriptions",
                    "unsubscribe_brand",
                    "get_delta_report",
                ],
            },
        ],
        "requirements": [
            "Claude Code (CLI / IDE extension) or Claude API access",
            "Claude Opus 4.7 recommended for the Lead role; Sonnet 4.6 works for sub-agents",
            "Optional: 阿里云无影 AgentBay for the Wuying cloud-browser leg (X / RedNote / Bilibili / Chinese press signal)",
        ],
    }


def build_index(counts: dict) -> dict:
    return {
        "site": "mbabrand.com",
        "name": "MBA — Metric Brand Auditor",
        "tagline": "Brand judgment for the agentic age — scored, versioned, replayable.",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "counts": counts,
        "endpoints": {
            "manifest":    "/api/index.json",
            "about":       "/api/about.json",
            "methodology": "/api/methodology.json",
            "reports":     "/api/reports.json",
            "report":      "/api/reports/{slug}.json",
            "panels":      "/api/panels.json",
            "panel":       "/api/panels/{slug}.json",
            "judges":      "/api/judges.json",
            "judge":       "/api/judges/{slug}.json",
            "install":     "/api/install.json",
            "search":      "/api/search.json",
        },
        "cors": "open (Access-Control-Allow-Origin: *)",
        "auth": "none",
        "format": "application/json; charset=utf-8",
        "discovery": "/llms.txt",
        "human_intro": "/agents.html",
    }


def build_search(judges: list[dict], panels: list[dict], reports: list[dict], methodology: dict) -> dict:
    items = []
    for r in reports:
        items.append({
            "type": "report",
            "slug": r["slug"],
            "title": f"{r.get('brand_cn') or r.get('brand_en')} · {r['version']}",
            "text": r.get("tl_dr", ""),
            "url": r["html_url"],
            "api_url": r["api_url"],
        })
    for p in panels:
        items.append({
            "type": "panel",
            "slug": p["slug"],
            "title": p["display_name"],
            "text": p.get("description", ""),
            "url": p["api_url"],
            "api_url": p["api_url"],
        })
    for j in judges:
        items.append({
            "type": "judge",
            "slug": j["slug"],
            "title": j["name"],
            "text": j.get("summary", ""),
            "url": j["api_url"],
            "api_url": j["api_url"],
        })
    for d in methodology["dimensions"]:
        items.append({
            "type": "dimension",
            "slug": d["slug"],
            "title": f"Dim {d['n']}: {d['name_en']}",
            "text": f"{d['tier']} dimension #{d['n']}",
            "url": "/how-it-works.html#dimensions",
            "api_url": "/api/methodology.json",
        })
    for l in methodology["lenses"]:
        items.append({
            "type": "lens",
            "slug": l["slug"],
            "title": f"Lens {l['n']}: {l['name_en']}",
            "text": l["description"],
            "url": "/how-it-works.html#lenses",
            "api_url": "/api/methodology.json",
        })
    return {"count": len(items), "items": items}


# ----------------------------------------------------------- llms.txt ------

# Curated prose template; counts (__N_PANELS__ / __N_JUDGES__) are filled from
# the same source data as /api so they can never drift (this is what caused the
# old hardcoded "11 panels" bug). Placeholders (not f-string) keep the jq `{...}`
# examples literal.
LLMS_TXT_TEMPLATE = """\
# mbabrand.com

> MBA — Metric Brand Auditor. AI 时代的品牌影响力审计协议。
> 多智能体并行调研 + N 评委独立打分 + 版本化报告。
> 不只是给人看的报告站,也是给 agent 调用的品牌判断接口。

## For AI agents

Agent 不用抓 HTML。所有结构化内容在 build 时落成静态 JSON,挂在 `/api/*.json`。
HTTP GET 直接拿,CORS 全开,无 token。

- /api/index.json — manifest:counts + 所有端点 URL
- /api/about.json — MBA 是什么 + team + repo + install
- /api/methodology.json — 7 维度 + 5 镜头 + 5 阶段流水线的结构化描述
- /api/reports.json — 已发布的品牌审计报告列表(slug / 品牌 / 版本 / 总分 / TL;DR)
- /api/reports/{slug}.json — 单个报告的元数据 + html_url + pdf_url
- /api/panels.json — __N_PANELS__ 个内置评委 panel + 行业映射表
- /api/panels/{slug}.json — 单个 panel 的评委组成 + 触发条件
- /api/judges.json — __N_JUDGES__ 个评委人物视角 skill
- /api/judges/{slug}.json — 单个评委的来源 SKILL.md + 视角描述
- /api/install.json — 怎么把 MBA 装进 Claude Code(BotLearn / GitHub)
- /api/search.json — 扁平语料:reports + panels + judges + dimensions + lenses,给客户端 substring search

## Human-facing pages

- /agents.html — 给 agent 工程师看的接入指南(端点表 + curl 示例 + Claude Code 集成)
- /presentation/ — 21 页编辑式 deck(为什么 / 怎么做 / 评委 / 商业化)
- /pitch.html — 5 分钟现场讲稿
- /how-it-works.html — 7 × 5 打分体系详解 + 流程图
- /reports/{slug}/ — 单个 audit 报告的人类可读 HTML 版

## Quick start

```sh
# 拿全站 manifest
curl -s https://mbabrand.com/api/index.json

# 列出所有已发布的报告
curl -s https://mbabrand.com/api/reports.json | jq '.items[] | {slug, brand_cn, version}'

# 读联想的审计 meta
curl -s https://mbabrand.com/api/reports/lenovo.json

# 查 auto panel 里有谁
curl -s https://mbabrand.com/api/panels/auto.json | jq '.judges[].display_name_cn'

# 拿单个评委的 SKILL.md 描述
curl -s https://mbabrand.com/api/judges/jobs.json | jq -r .description
```

## Trigger MBA from your own agent

MBA 本身是一个 Claude Code skill。给自己的 agent 内置「读 mbabrand.com」之后,
更进一步可以触发新的审计运行:

```
/mba <brand-slug>             # 在 Claude Code 里全流程跑一份新报告
/mba <brand> --refresh         # EVOLUTION 模式:只重跑变了的维度
/mba <brand> --quick --no-judges  # 单视角速读,不召评委
```

Install: https://www.botlearn.ai/en/community/u/mba_auditor
Source:  https://github.com/zhanglunet/mba

License: Apache-2.0
Disclaimer: 评委头像 / 评分 / verdict / 辩论均为 AI 基于公开一手资料的 in-character
模拟,非本人真实意见。报告不构成投资建议。
"""


def build_llms_txt(n_panels: int, n_judges: int) -> str:
    return (LLMS_TXT_TEMPLATE
            .replace("__N_PANELS__", str(n_panels))
            .replace("__N_JUDGES__", str(n_judges)))


# ---------------------------------------------------------------- main -----

def main() -> int:
    # Clean old api/ output so removed entries don't linger. (Skipped under
    # --check: we must not delete the committed files we're validating.)
    if not CHECK_MODE and API_DIR.exists():
        for p in sorted(API_DIR.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
    API_DIR.mkdir(parents=True, exist_ok=True)

    judges_list, judges_bodies = build_judges()
    panels_list, panels_bodies, industries = build_panels(judges_bodies)
    methodology = build_methodology()
    reports_list, reports_bodies = build_reports()
    about = build_about()
    install = build_install()

    counts = {
        "reports": len(reports_list),
        "panels": len(panels_list),
        "judges": len(judges_list),
        "dimensions": len(methodology["dimensions"]),
        "lenses": len(methodology["lenses"]),
        "industries": len(industries),
    }

    write_json("index.json", build_index(counts))
    write_json("about.json", about)
    write_json("install.json", install)
    write_json("methodology.json", methodology)

    write_json("reports.json", {"count": len(reports_list), "items": reports_list})
    for slug, body in reports_bodies.items():
        write_json(f"reports/{slug}.json", body)

    write_json(
        "panels.json",
        {"count": len(panels_list), "industries": industries, "items": panels_list},
    )
    for slug, body in panels_bodies.items():
        write_json(f"panels/{slug}.json", body)

    write_json("judges.json", {"count": len(judges_list), "items": judges_list})
    for slug, body in judges_bodies.items():
        write_json(f"judges/{slug}.json", body)

    write_json(
        "search.json",
        build_search(judges_list, panels_list, reports_list, methodology),
    )

    # llms.txt — generated from the same counts so it can't drift (outside api/).
    write_text_file(
        SITE_DIR / "llms.txt",
        build_llms_txt(len(panels_list), len(judges_list)),
        "llms.txt",
    )

    if CHECK_MODE:
        # Flag committed files the generator no longer produces (stale leftovers).
        for p in sorted(API_DIR.rglob("*.json")):
            rel = str(p.relative_to(API_DIR))
            if rel not in _PRODUCED:
                DRIFT.append(f"stale:   api/{rel} (in repo, generator no longer produces it)")
        if DRIFT:
            print("[agents-api] CHECK FAILED — site/api/ is out of sync with sources:",
                  file=sys.stderr)
            for d in DRIFT:
                print("  " + d, file=sys.stderr)
            print("Fix: run `python3 scripts/build_agents_api.py` and commit site/api/.",
                  file=sys.stderr)
            return 1
        print(f"[agents-api] check OK — api/ in sync with sources "
              f"({counts['judges']} judges / {counts['panels']} panels / {counts['reports']} reports)")
        return 0

    print(f"[agents-api] done — "
          f"{counts['reports']} reports, "
          f"{counts['panels']} panels, "
          f"{counts['judges']} judges, "
          f"{counts['dimensions']} dimensions, "
          f"{counts['lenses']} lenses")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build (or --check) mbabrand.com agent-facing JSON API.")
    ap.add_argument(
        "--check", action="store_true",
        help="Verify committed site/api/ matches generator output and exit 1 on "
             "drift (ignores index.json generated_at). Writes nothing.",
    )
    CHECK_MODE = ap.parse_args().check
    sys.exit(main())
