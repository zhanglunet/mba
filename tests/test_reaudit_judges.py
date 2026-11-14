import importlib.util
import pathlib
import sys
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / 'scripts/watch-tools'
sys.path.insert(0, str(path))
spec = importlib.util.spec_from_file_location('reaudit_judges', path / 'reaudit_judges.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class JudgeGateTest(unittest.TestCase):
    def test_requires_verified_cited_evidence_and_bounded_scores(self):
        evidence = [{'id':'e1', 'verification':'verified', 'verification_source':'https://example.com/source', 'verification_excerpt':'evidence', 'verification_reason':'reviewed'}]
        result = {'judge':'paulg', 'scores':dict.fromkeys(mod.LENSES, 8), 'evidence_ids':['e1'], 'reason':'Evidence supports judgment.'}
        mod.validate_judgment(result, 'paulg', evidence)
        result['scores']['signal'] = 11
        with self.assertRaises(ValueError): mod.validate_judgment(result, 'paulg', evidence)
        result['scores']['signal'] = 8
        with self.assertRaises(ValueError): mod.validate_judgment(result, 'paulg', [{'id':'e1', 'verification':'unverified'}])

    def test_requires_exact_judge_and_all_lenses(self):
        with self.assertRaises(ValueError): mod.validate_judgment({'judge':'wrong', 'scores':{}, 'reason':'x', 'evidence_ids':['e1']}, 'paulg', [])

class LensEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.evidence = [{'id':'e1', 'date':'2026-08-04', 'verification':'verified', 'verification_source':'https://example.com/source', 'verification_excerpt':'evidence', 'verification_reason':'reviewed'}]
        self.baseline = dict.fromkeys(mod.LENSES, 8)
        self.result = {'judge':'paulg', 'scores':dict(self.baseline), 'reason':'review', 'lens_evidence':{lens: [] for lens in mod.LENSES}, 'lens_reasons':{lens: 'unchanged' for lens in mod.LENSES}, 'as_of':'2026-11-13'}

    def test_changed_score_needs_lens_specific_evidence(self):
        self.result['scores']['signal'] = 7
        with self.assertRaises(ValueError): mod.validate_judgment(self.result, 'paulg', self.evidence, self.baseline)
        self.result['lens_evidence']['signal'] = ['e1']
        mod.validate_judgment(self.result, 'paulg', self.evidence, self.baseline)

    def test_evidence_from_future_is_rejected(self):
        self.result['scores']['signal'] = 7
        self.result['lens_evidence']['signal'] = ['e1']
        self.result['as_of'] = '2026-08-01'
        with self.assertRaises(ValueError): mod.validate_judgment(self.result, 'paulg', self.evidence, self.baseline)

class RetryTest(unittest.TestCase):
    def test_invalid_model_output_is_retried(self):
        from unittest.mock import patch
        with patch.object(mod.llm, 'call_llm', side_effect=[ValueError('bad JSON'), [{'ok': True}]]) as call:
            self.assertEqual(mod.call_with_retry([], ('x','key','url','model'), 'system'), [{'ok': True}])
            self.assertEqual(call.call_count, 2)

class BaselineConsistencyTest(unittest.TestCase):
    def test_report_and_panel_versions_must_match_baseline(self):
        baseline = {'version':'v3','scores':{name:dict.fromkeys(mod.LENSES, 8) for name in mod.JUDGES}}
        with self.assertRaisesRegex(ValueError, 'baseline version'):
            mod.validate_baseline(baseline, {'version':'v4','score_total':200})

    def test_panel_total_must_match_baseline_matrix(self):
        baseline = {'version':'v4','scores':{name:dict.fromkeys(mod.LENSES, 8) for name in mod.JUDGES}}
        with self.assertRaisesRegex(ValueError, 'baseline total'):
            mod.validate_baseline(baseline, {'version':'v4','score_total':213})
        mod.validate_baseline(baseline, {'version':'v4','score_total':200})

class BaselineExtractionTest(unittest.TestCase):
    def test_extracts_matrix_in_vc_en_order(self):
        rows = ['## Score Matrix','| Lens | 安德森 | 格雷厄姆 | 蒂尔 | 纳瓦尔 | 霍夫曼 | Mean |','|---|---|---|---|---|---|---|']
        for lens in mod.LENSES: rows.append('| '+lens+' | 9 | 8 | 7 | 6 | 5 | 7.0 |')
        rows.append('## Next')
        baseline = mod.baseline_from_report('\n'.join(rows), {'version':'v4','score_total':175})
        self.assertEqual(baseline['scores']['pmarca']['origin'],9)
        self.assertEqual(baseline['scores']['rhoffman']['signal'],5)

    def test_missing_matrix_is_rejected(self):
        with self.assertRaises(ValueError): mod.baseline_from_report('no matrix', {'version':'v4','score_total':1})

class FreshEvidenceTest(unittest.TestCase):
    def test_only_verified_evidence_after_baseline_and_before_review(self):
        evidence=[{'id':'old','date':'2026-11-14','verification':'verified'}, {'id':'new','date':'2026-11-15','verification':'verified'}, {'id':'future','date':'2026-11-18','verification':'verified'}, {'id':'unverified','date':'2026-11-15','verification':'unverified'}]
        selected=mod.fresh_evidence(evidence, '2026-11-14', '2026-11-16')
        self.assertEqual([e['id'] for e in selected],['new'])
