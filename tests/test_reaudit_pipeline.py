import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/watch-tools'))
import reaudit_evidence as ev
import reaudit_judges as judges
import reaudit_review as review
import reaudit_report as report

class PipelineTest(unittest.TestCase):
    def test_evidence_to_draft_and_reject_tampering(self):
        event={'id':'e1','title':'Launch','quote':'Launch','date':'2026-11-15','url':'https://blogs.nvidia.com/blog/launch/','source_type':'official'}
        source={'fetch_status':'ok','quote_match':True,'source_date':'2026-11-15','source_title':'Launch','final_url':event['url']}
        evidence=[ev.official_statement_evidence(event,source)]
        baseline={'version':'v4','scores':{judge:dict.fromkeys(judges.LENSES,8) for judge in judges.JUDGES}}
        provider=('openai','fake','https://example.com','model')
        def simulate(items, provider, system):
            judge=items[0]['judge']; scores=dict(baseline['scores'][judge]); scores['signal']=7
            return [{'judge':judge,'as_of':'2026-11-16','scores':scores,'reason':'review','lens_evidence':{lens:(['e1'] if lens=='signal' else []) for lens in judges.LENSES},'lens_reasons':dict.fromkeys(judges.LENSES,'explanation')}]
        with patch.object(judges,'call_with_retry',side_effect=simulate):
            js=judges.generate_judgments('old report',evidence,provider,baseline['scores'],'2026-11-16')
        def critic(items, provider, system, max_tokens, timeout):
            return [{'judge':item['judge'],'lens':item['lens'],'verdict':'supported','reason':'source'} for item in items]
        with patch.object(review.llm,'call_llm',side_effect=critic):
            result=review.critique(js,evidence,baseline['scores'],provider)
        result.update(judgments_sha256=report.judgment_hash(js),evidence_sha256=report.evidence_hash(evidence))
        draft={'status':'draft','brand':'nvidia','baseline':baseline,'evidence_sha256':report.evidence_hash(evidence),'judgments':js}
        self.assertIn('195/250', report.build_draft(draft,result,baseline,evidence))
        evidence[0]['verification_excerpt']='tampered'
        with self.assertRaisesRegex(ValueError,'evidence differs'): report.build_draft(draft,result,baseline,evidence)
