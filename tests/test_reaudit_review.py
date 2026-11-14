import importlib.util
import pathlib
import sys
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / 'scripts/watch-tools'
sys.path.insert(0, str(path))
spec = importlib.util.spec_from_file_location('reaudit_review', path / 'reaudit_review.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ReviewTest(unittest.TestCase):
    def test_missing_or_duplicate_review_blocks(self):
        required = [('paulg', 'origin'), ('paulg', 'signal')]
        good = [{'judge':'paulg','lens':'origin','verdict':'supported','reason':'ok'}, {'judge':'paulg','lens':'signal','verdict':'unsupported','reason':'wrong date'}]
        self.assertFalse(mod.validate_reviews(good, required))
        with self.assertRaises(ValueError): mod.validate_reviews(good[:1], required)
        with self.assertRaises(ValueError): mod.validate_reviews([good[0],good[0]], required)

    def test_supported_results_are_valid_but_remain_draft(self):
        self.assertTrue(mod.validate_reviews([{'judge':'j','lens':'signal','verdict':'supported','reason':'source'}], [('j','signal')]))
        with self.assertRaises(ValueError): mod.validate_reviews([{'judge':'j','lens':'signal','verdict':'supported','reason':''}], [('j','signal')])

class DynamicRosterTest(unittest.TestCase):
    def test_critique_accepts_the_baseline_roster(self):
        from unittest.mock import patch
        roster=('zhuxiaohu','zhanglei'); lenses=('origin','category','leverage','identity','signal')
        baseline={j:dict.fromkeys(lenses,8) for j in roster}
        evidence=[{'id':'e1','date':'2026-11-15','verification':'verified','verification_source':'https://example.com','verification_excerpt':'x','verification_reason':'reviewed'}]
        judgments=[]
        for judge in roster:
            scores=dict(baseline[judge]);scores['signal']=7
            judgments.append({'judge':judge,'scores':scores,'as_of':'2026-11-16','reason':'x','lens_evidence':{k:(['e1'] if k=='signal' else []) for k in lenses},'lens_reasons':dict.fromkeys(lenses,'x')})
        def response(items,prov,system,max_tokens,timeout):
            return [{'judge':x['judge'],'lens':x['lens'],'verdict':'supported','reason':'ok'} for x in items]
        with patch.object(mod.llm,'call_llm',side_effect=response):
            self.assertEqual(mod.critique(judgments,evidence,baseline,('x','key','url','model'))['evidence_review'],'passed')
