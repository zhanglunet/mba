#!/usr/bin/env python3
"""
自动检查生成的SKILL.md是否通过Phase 4质量标准。
对照通过标准表格逐项检查，输出通过/不通过和具体原因。

用法:
    python3 quality_check.py <SKILL.md路径>

示例:
    python3 quality_check.py .claude/skills/elon-musk-perspective/SKILL.md
"""

import sys
import re
from pathlib import Path


def check_mental_models(content: str) -> tuple[bool, str]:
    """检查心智模型数量（SOP §3 门槛：≥6 个 ### 模型N）。

    F8 收紧:原来接受 3-7,一个只写 3 个模型的偷懒 SKILL 也能过;深化 SOP 明确要求
    「6 个 ### 模型N」,故 gate 提到 ≥6(43 套 full 均已达 6)。"""
    # 匹配 ### 模型N: 或 ### N. 等模式
    models = re.findall(r'^###\s+(?:模型|Model|心智模型)\s*\d', content, re.MULTILINE)
    if not models:
        # fallback: 数「### 」开头的行在心智模型section中
        in_section = False
        count = 0
        for line in content.split('\n'):
            if re.match(r'^##\s+.*心智模型|Mental Model', line, re.IGNORECASE):
                in_section = True
                continue
            if in_section and re.match(r'^##\s+', line) and '心智模型' not in line:
                break
            if in_section and re.match(r'^###\s+', line):
                count += 1
        if count > 0:
            passed = count >= 6
            return passed, f"{count}个心智模型 {'✅' if passed else '❌ (应≥6个, SOP §3)'}"

    count = len(models)
    if count == 0:
        return False, "未检测到心智模型section"
    passed = count >= 6
    return passed, f"{count}个心智模型 {'✅' if passed else '❌ (应≥6个, SOP §3)'}"


def check_limitations(content: str) -> tuple[bool, str]:
    """检查每个模型是否有局限性"""
    has_limitation = bool(re.search(r'局限|失效|不适用|盲区|limitation|blind spot', content, re.IGNORECASE))
    return has_limitation, "有局限性标注 ✅" if has_limitation else "❌ 未找到局限性描述"


_DNA_FACETS = ('句式', '词汇', '语气', '幽默', '节奏', '确定性', '引用', '口头禅')

def check_expression_dna(content: str) -> tuple[bool, str]:
    """检查表达DNA辨识度（≥3 个**不同** facet,且必须落在表达DNA section 内）。

    F8 收紧:原来数「这 8 个词在全文出现几次」——把「句式」写 3 遍即可假过,且不限区段。
    改为在表达DNA section 内数**去重后**的 facet 类型(句式/词汇/语气/…),要求 ≥3 个不同维度,
    杜绝「计词而非计实质」。"""
    m = re.search(r'(##\s+.*(?:表达DNA|Expression DNA|表达风格).*?)(?=\n##\s|\Z)',
                  content, re.DOTALL | re.IGNORECASE)
    if not m:
        return False, "❌ 未找到表达DNA section"
    section = m.group(1)
    distinct = [k for k in _DNA_FACETS if k in section]
    passed = len(distinct) >= 3
    shown = '/'.join(distinct) if distinct else '无'
    return passed, f"表达DNA不同维度: {len(distinct)}项({shown}) {'✅' if passed else '❌ (section 内应≥3个不同 facet)'}"


def check_honest_boundary(content: str) -> tuple[bool, str]:
    """检查诚实边界（至少3条）"""
    # 找诚实边界section
    boundary_match = re.search(r'(?:##\s+.*诚实边界|## Honest Boundary)(.*?)(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
    if not boundary_match:
        return False, "❌ 未找到诚实边界section"

    boundary_text = boundary_match.group(1)
    # 计算列表项
    items = re.findall(r'^[-*]\s+', boundary_text, re.MULTILINE)
    count = len(items)
    passed = count >= 3
    return passed, f"诚实边界: {count}条 {'✅' if passed else '❌ (应≥3条)'}"


_TENSION_PAT = re.compile(r'张力|矛盾|tension|paradox|一方面.*?另一方面|既.*?又', re.IGNORECASE)

def check_tensions(content: str) -> tuple[bool, str]:
    """检查内在张力（至少 2 条,分布在 ≥2 个**不同行**）。

    F8 收紧:原来数关键词总出现次数——同一句里写两遍「矛盾」即假过。改为数**含张力标记的
    不同行数**,要求 ≥2 行,确保是两条独立的张力而非一句话里的重复词。"""
    # 排除 H2 区段标题行(如「## 内在张力」——它只命名区段、不是一条张力),
    # 但保留 ### 张力N 子标题(每个即一条张力)与正文行。
    lines_with = [ln for ln in content.split('\n')
                  if _TENSION_PAT.search(ln) and not re.match(r'^\s*##\s+(?!#)', ln)]
    count = len(lines_with)
    passed = count >= 2
    return passed, f"内在张力: {count}条(不同行) {'✅' if passed else '❌ (应≥2条,分布在不同行)'}"


def check_primary_sources(content: str) -> tuple[bool, str]:
    """检查一手来源占比"""
    # 找调研来源section
    source_section = re.search(r'(?:##\s+.*来源|## Source|## Reference)(.*?)(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
    if not source_section:
        return True, "未找到来源section（跳过检查）"

    source_text = source_section.group(1)
    primary = len(re.findall(r'一手|primary|本人著作|原始', source_text, re.IGNORECASE))
    secondary = len(re.findall(r'二手|secondary|转述|评论', source_text, re.IGNORECASE))
    total = primary + secondary
    if total == 0:
        return True, "未标记来源类型（跳过检查）"

    ratio = primary / total
    passed = ratio > 0.5
    return passed, f"一手来源占比: {primary}/{total} ({ratio:.0%}) {'✅' if passed else '❌ (应>50%)'}"


# ── F8: 收紧后的 gate 有没有「牙」——负样本自测 ────────────────────────────────
# 证明三项收紧真能拦住旧的假过样本(旧阈值下它们都能过)。合成假 SKILL,断言对应 check 判 FAIL;
# 一个合规样本断言 PASS。接 panel-validation.yml,收紧退化(有人把阈值调回去)即红。
_GOOD = """## 核心心智模型
### 模型 1：甲
### 模型 2：乙
### 模型 3：丙
### 模型 4：丁
### 模型 5：戊
### 模型 6：己  局限：此模型在 X 情况失效
## 表达DNA
- 句式：短促断言
- 词汇：新造术语
- 语气：笃定
## 诚实边界
- 边界一
- 边界二
- 边界三
## 内在张力
- 张力：既要快又要稳
- 矛盾：叙事跑在产品前面
## 调研来源
- 一手：本人著作 / 采访原话
"""

_FAKE_MODELS = _GOOD.replace("### 模型 4：丁\n", "").replace("### 模型 5：戊\n", "").replace("### 模型 6：己  局限：此模型在 X 情况失效\n", "局限：留一句\n")  # 只剩 3 个模型
_FAKE_DNA = _GOOD.replace("- 句式：短促断言\n- 词汇：新造术语\n- 语气：笃定\n", "- 句式：一\n- 句式：二\n- 句式：三\n")  # 同一 facet 重复 3 次(旧法计 3 次通过)
_FAKE_TENSION = _GOOD.replace("- 张力：既要快又要稳\n- 矛盾：叙事跑在产品前面\n", "- 张力矛盾张力矛盾（同一行堆两遍）\n")  # 同一行多次 + 只剩 H2 标题(被排除)→ 有效行仅 1(旧法计 ≥2 通过)

def selftest() -> int:
    cases = [
        ("合规样本 → 6/6", _GOOD, None, True),
        ("3 个模型(旧 3-7 可过)→ 心智模型 FAIL", _FAKE_MODELS, check_mental_models, False),
        ("DNA 同一 facet 重复(旧计词可过)→ 表达DNA FAIL", _FAKE_DNA, check_expression_dna, False),
        ("张力堆同一行(旧计次可过)→ 内在张力 FAIL", _FAKE_TENSION, check_tensions, False),
    ]
    print("quality_check 负样本自测(F8 收紧有牙)")
    print("=" * 50)
    ok = True
    for name, content, fn, expect in cases:
        if fn is None:
            checks = [check_mental_models, check_expression_dna, check_honest_boundary,
                      check_tensions, check_primary_sources]
            got = all(c(content)[0] for c in checks)
        else:
            got = fn(content)[0]
        status = "✅" if got == expect else "❌"
        if got != expect:
            ok = False
        print(f"  {status} {name}  (期望 pass={expect}, 实得 pass={got})")
    print("=" * 50)
    print("✅ 自测通过:收紧项对旧假过样本有牙。" if ok else "❌ 自测失败:某项收紧未拦住假过样本。")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    if len(sys.argv) < 2:
        print("用法: python3 quality_check.py <SKILL.md路径> | --selftest")
        sys.exit(1)

    skill_path = Path(sys.argv[1])
    if not skill_path.exists():
        print(f"❌ 文件不存在: {skill_path}")
        sys.exit(1)

    content = skill_path.read_text(encoding='utf-8')

    checks = [
        ("心智模型数量", check_mental_models),
        ("模型局限性", check_limitations),
        ("表达DNA辨识度", check_expression_dna),
        ("诚实边界", check_honest_boundary),
        ("内在张力", check_tensions),
        ("一手来源占比", check_primary_sources),
    ]

    print(f"质量检查: {skill_path.name}")
    print("=" * 50)

    passed_count = 0
    total = len(checks)

    for name, check_fn in checks:
        passed, detail = check_fn(content)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<12} {status}  {detail}")
        if passed:
            passed_count += 1

    print("=" * 50)
    print(f"结果: {passed_count}/{total} 通过")

    if passed_count == total:
        print("🎉 全部通过，可以交付")
    elif passed_count >= total - 1:
        print("⚠️ 基本通过，建议修复不通过项后交付")
    else:
        print("❌ 多项不通过，建议回到Phase 2迭代")

    sys.exit(0 if passed_count == total else 1)


if __name__ == '__main__':
    main()
