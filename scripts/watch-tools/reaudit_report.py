#!/usr/bin/env python3
"""Build a review-only report; never update published reports or event state."""
import argparse
import hashlib
import json
from pathlib import Path
from reaudit_judges import JUDGES, LENSES, validate_judgment
from reaudit_review import validate_reviews


def judgment_hash(judgments):
    return hashlib.sha256(json.dumps(judgments, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def evidence_hash(evidence):
    return judgment_hash(evidence)


def ensure_complete_review(required, review):
    if review.get('evidence_review') != 'passed':
        raise ValueError('evidence review did not pass')
    if not validate_reviews(review.get('reviews'), required):
        raise ValueError('unsupported score change')


def build_draft(draft, review, baseline, evidence):
    if draft.get('status') != 'draft' or draft.get('baseline') != baseline:
        raise ValueError('draft baseline mismatch')
    judgments = draft.get('judgments')
    if not isinstance(judgments, list) or len(judgments) != len(JUDGES) or {j.get('judge') for j in judgments} != set(JUDGES):
        raise ValueError('judge roster mismatch')
    if review.get('judgments_sha256') != judgment_hash(judgments):
        raise ValueError('review does not match judgments')
    if draft.get('evidence_sha256') != evidence_hash(evidence) or review.get('evidence_sha256') != evidence_hash(evidence):
        raise ValueError('review evidence differs from scoring evidence')
    scores = baseline['scores']
    changed = []
    for judgment in judgments:
        judge = judgment['judge']
        validate_judgment(judgment, judge, evidence, scores[judge])
        changed.extend((judge, lens) for lens in LENSES if judgment['scores'][lens] != scores[judge][lens])
    ensure_complete_review(changed, review)
    by_judge = {j['judge']: j for j in judgments}
    total = sum(sum(j['scores'].values()) for j in judgments)
    previous = sum(sum(j.values()) for j in scores.values())
    out = ['# NVIDIA 自动重审草稿', '', '**状态：待人工复核，未发布。** 评委与证据复核均为 AI 模拟。', '',
           f'基线 {baseline["version"]}: {previous}/250；本轮提案 {total}/250（{total/25:.2f}/10）。', '',
           '| Lens | '+ ' | '.join(JUDGES)+' | 均分 |', '|---|---:|---:|---:|---:|---:|---:|']
    for lens in LENSES:
        vals = [by_judge[j]['scores'][lens] for j in JUDGES]
        out.append('| '+lens+' | '+' | '.join(map(str, vals))+' | '+f'{sum(vals)/5:.1f}'+' |')
    out += ['', '## 逐项变化与证据', '']
    for judge, lens in changed:
        item = by_judge[judge]
        out.append(f'- {judge} / {lens}: {scores[judge][lens]} → {item["scores"][lens]}；{item["lens_reasons"][lens]}；事件：{", ".join(item["lens_evidence"][lens])}')
    if not changed:
        out.append('- 没有评分变化。')
    out += ['', '## 限制', '', '来源核验、评分理由和时序仍需人工检查；模型复核不保证事实或判断正确。', '']
    return '\n'.join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('draft','review','evidence','output'):
        p.add_argument('--'+arg, type=Path, required=True)
    a=p.parse_args()
    read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    draft, review, evidence=read(a.draft),read(a.review),read(a.evidence)
    result=build_draft(draft,review,draft['baseline'],evidence)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(result,encoding='utf-8')
    print('Draft saved:',a.output)

if __name__ == '__main__':
    main()
