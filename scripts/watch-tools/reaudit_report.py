#!/usr/bin/env python3
"""Build a review-only report; never update published reports or event state."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from reaudit_judges import JUDGES, LENSES, validate_judgment
from reaudit_review import validate_reviews
from reaudit_evidence import validate_score_evidence


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
    roster = list(baseline.get('scores', {}))
    if not roster or not isinstance(judgments, list) or len(judgments) != len(roster) or {j.get('judge') for j in judgments} != set(roster):
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
    maximum = len(roster) * 50
    brand = draft.get('brand') or 'unknown'
    out = [f'# {brand} 自动重审草稿', '', '**状态：待人工复核，未发布。** 评委与证据复核均为 AI 模拟。', '',
           f'基线 {baseline["version"]}: {previous}/{maximum}；本轮提案 {total}/{maximum}（{total*10/maximum:.2f}/10）。', '',
           '| Lens | '+ ' | '.join(roster)+' | 均分 |', '|---|'+'---:|'*(len(roster)+1)]
    for lens in LENSES:
        vals = [by_judge[j]['scores'][lens] for j in roster]
        out.append('| '+lens+' | '+' | '.join(map(str, vals))+' | '+f'{sum(vals)/len(roster):.1f}'+' |')
    out += ['', '## 本轮来源', '', '自动匹配仅确认官方陈述存在，不代表独立事实核验。', '']
    referenced = {event_id for j in judgments for ids in j['lens_evidence'].values() for event_id in ids}
    by_id = {item['id']: item for item in evidence}
    eligible = {item['id'] for item in evidence if item.get('verification') == 'verified'}
    for event_id in sorted(eligible):
        validate_score_evidence([event_id], evidence)
        item = by_id[event_id]
        title = html.escape(str(item.get('title') or event_id)).replace('[', r'\[').replace(']', r'\]').replace('\n', ' ')
        url = str(item['verification_source']).replace('>', '%3E').replace(' ', '%20')
        out.append(f'- {event_id} · {item.get("date", "")} · {title} · <{url}>')
    if not eligible:
        out.append('- 无可归因来源；需人工检查输入。')
    if not referenced:
        out.append('- 评委未引用任何事件；需人工检查输入及理由。')
    out += ['', '## 评委总体理由', '', '以下为 AI 模拟原文，可能包含未经核验的事实或关系判断，不能视为人物本人意见。', '']
    for judge in roster:
        reason = html.escape(by_judge[judge]['reason']).replace('\n', ' ').replace('[', r'\[').replace(']', r'\]')
        out.append(f'- **{judge}**：{reason}')
    out += ['', '## 逐项变化与证据', '']
    for judge, lens in changed:
        item = by_judge[judge]
        out.append(f'- {judge} / {lens}: {scores[judge][lens]} → {item["scores"][lens]}；{item["lens_reasons"][lens]}；事件：{", ".join(item["lens_evidence"][lens])}')
    if not changed:
        out.append('- 没有评分变化；本次证据复核只检查改分项，未对维持不变的评分进行独立复核。')
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
