# PRD-022/T1：mba panel 独立验收测试规范（草稿 v1）

> 依据：`metric-brand-auditor/panels/` 下 11 个 panel yaml 的真实结构（以 `default.yaml` 为例），
> 借鉴 K-Dense-AI/scientific-agent-skills 独立测试思路（MIT）。

## 一、测什么（每个 panel 一个测试文件）

`tests/panels/test_<panel名>.py`，只做静态检查，不调 LLM、不跑真实打分：

| # | 检查项 | 说明 |
|---|---|---|
| 1 | YAML 可解析 | `yaml.safe_load` 不抛异常 |
| 2 | 顶层字段齐全 | `name`、`display_name`、`description`、`judges` 四字段存在 |
| 3 | `name` 与文件名一致 | `default.yaml` 里 `name: default` |
| 4 | 评委数量 | `judges` 为非空 list（default 应为 5 人） |
| 5 | 评委字段齐全 | 每位评委含 `slug`、`display_name_cn`、`display_name_en`、`language`、`weight` |
| 6 | slug 唯一 | 同一 panel 内无重复 slug |
| 7 | weight 合法 | 每位 `0 < weight <= 2.0` 的数字 |

## 二、结构契约测试（`tests/_contract/test_panels.py`）

| # | 检查项 | 说明 |
|---|---|---|
| 1 | 注册清单一致 | panels/ 下的 yaml 文件集合 == README/索引中声明的 panel 集合（11 个） |
| 2 | 跨 panel 无重复评委 | 11 个 panel 的评委 slug 全局无重复（同名不同人须显式区分，如 `fusheng` 只出现一次） |
| 3 | portrait 文件存在 | 每位评委的 `portrait` 引用的图片文件真实存在（default 引用 `傅盛.jpg` 等 5 张） |

## 三、不测什么

- 不调 LLM 跑真实打分（贵、不稳定）。
- 不断言评委"视角"文案质量（自然语言，无强断言）。
- 不测报告渲染（report.html 是另一条链路）。

## 四、示例：default panel 测试（可直接跑）

```python
# tests/panels/test_default.py
import pathlib
import yaml

PANEL = pathlib.Path("metric-brand-auditor/panels/default.yaml")

def load():
    return yaml.safe_load(PANEL.read_text(encoding="utf-8"))

def test_yaml_parses():
    assert isinstance(load(), dict)

def test_top_level_fields():
    d = load()
    for k in ("name", "display_name", "description", "judges"):
        assert k in d, f"missing field: {k}"

def test_name_matches_filename():
    assert load()["name"] == "default"

def test_judge_count():
    judges = load()["judges"]
    assert isinstance(judges, list) and len(judges) == 5

def test_judge_fields():
    for j in load()["judges"]:
        for k in ("slug", "display_name_cn", "display_name_en", "language", "weight"):
            assert k in j, f"judge {j.get('slug')} missing field: {k}"

def test_slug_unique():
    slugs = [j["slug"] for j in load()["judges"]]
    assert len(slugs) == len(set(slugs)), "duplicate slug"

def test_weight_valid():
    for j in load()["judges"]:
        w = j["weight"]
        assert isinstance(w, (int, float)) and 0 < w <= 2.0, f"judge {j['slug']} bad weight: {w}"
```

## 五、落地步骤（T2 用）

1. 先合入本规范 + `test_default.py`（第一批 PR）。
2. 其余 10 个 panel 照抄 `test_default.py` 改文件名与期望人数，分 2 批 PR。
3. `tests/_contract/test_panels.py` 单独一个 PR。
4. 接入 `.github/` CI。
