#!/usr/bin/env python3
"""Evaluate watch triggers only for events newer than a report baseline."""
import argparse
import json
from datetime import date
from pathlib import Path
import yaml
import evaluate_triggers


def evaluate_new(events, baseline_date, as_of, baseline_ids=None):
    baseline = date.fromisoformat(str(baseline_date))
    today = date.fromisoformat(str(as_of))
    if today < baseline:
        raise ValueError('review date precedes baseline')
    fresh = [e for e in events if isinstance(e, dict) and evaluate_triggers.as_date(e.get('date')) and (evaluate_triggers.as_date(e['date']) > baseline or (baseline_ids is not None and evaluate_triggers.as_date(e['date']) == baseline and e.get('id') not in baseline_ids))]
    return evaluate_triggers.evaluate(fresh, today)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events',type=Path,required=True)
    parser.add_argument('--panel',type=Path,required=True)
    parser.add_argument('--as-of',required=True)
    parser.add_argument('--baseline-events',type=Path)
    args=parser.parse_args()
    panel=yaml.safe_load(args.panel.read_text(encoding='utf-8'))
    events=yaml.safe_load(args.events.read_text(encoding='utf-8'))
    baseline_events = yaml.safe_load(args.baseline_events.read_text(encoding='utf-8')) if args.baseline_events else None
    if baseline_events is not None and (not isinstance(baseline_events, list) or any(not isinstance(e, dict) or not e.get('id') for e in baseline_events)):
        raise ValueError('invalid baseline event snapshot')
    ids = {e['id'] for e in baseline_events} if baseline_events is not None else None
    print(json.dumps(evaluate_new(events,panel['published_at'],args.as_of,ids),ensure_ascii=False))

if __name__ == '__main__':
    main()
