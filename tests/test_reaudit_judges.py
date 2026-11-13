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
