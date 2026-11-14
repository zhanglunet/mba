import importlib.util
import pathlib
import sys
import unittest

path=pathlib.Path(__file__).resolve().parents[1]/'scripts/watch-tools'
sys.path.insert(0,str(path))
spec=importlib.util.spec_from_file_location('reaudit_report',path/'reaudit_report.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class DraftTest(unittest.TestCase):
    def test_rejects_failed_or_incomplete_evidence_review(self):
        with self.assertRaises(ValueError):
            mod.build_draft({'judgments': []}, {'evidence_review':'failed','reviews':[]}, {}, [])
    def test_missing_review_cannot_be_misrepresented_as_pass(self):
        with self.assertRaises(ValueError):
            mod.ensure_complete_review([('paulg','signal')], {'evidence_review':'passed','reviews':[]})

class ReviewBindingTest(unittest.TestCase):
    def test_evidence_digest_changes_when_source_changes(self):
        one=[{'id':'e1','verification_source':'https://example.com/one'}]
        two=[{'id':'e1','verification_source':'https://example.com/two'}]
        self.assertNotEqual(mod.evidence_hash(one), mod.evidence_hash(two))

class PipelineTest(unittest.TestCase):
    def test_bound_scoring_and_review_generate_draft(self):
        from reaudit_judges import JUDGES,LENSES
        baseline={'version':'v4','scores':{judge:{lens:8 for lens in LENSES} for judge in JUDGES}}
        evidence=[{'id':'e1','date':'2026-11-15','verification':'verified','verification_source':'https://example.com/a','verification_excerpt':'example','verification_reason':'reviewed'}]
        judgments=[]
        for judge in JUDGES:
            scores=dict(baseline['scores'][judge]); scores['signal']=7
            judgments.append({'judge':judge,'scores':scores,'reason':'review','as_of':'2026-11-16','lens_evidence':{lens:(['e1'] if lens=='signal' else []) for lens in LENSES},'lens_reasons':{lens:'explanation' for lens in LENSES}})
        draft={'status':'draft','baseline':baseline,'judgments':judgments,'evidence_sha256':mod.evidence_hash(evidence)}
        review={'evidence_review':'passed','judgments_sha256':mod.judgment_hash(judgments),'evidence_sha256':mod.evidence_hash(evidence),'reviews':[{'judge':judge,'lens':'signal','verdict':'supported','reason':'source'} for judge in JUDGES]}
        result=mod.build_draft(draft,review,baseline,evidence)
        self.assertIn('195/250',result)
        evidence[0]['verification_excerpt']='different'
        with self.assertRaisesRegex(ValueError,'evidence differs'):mod.build_draft(draft,review,baseline,evidence)
