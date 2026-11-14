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

class DynamicDraftTest(unittest.TestCase):
    def test_draft_uses_actual_panel_size_and_brand(self):
        from reaudit_judges import LENSES
        roster=['zhuxiaohu','zhanglei']
        baseline={'version':'v1','panel':'vc-cn','scores':{j:dict.fromkeys(LENSES,8) for j in roster}}
        evidence=[{'id':'e1','date':'2026-11-15','verification':'verified','verification_source':'https://example.com/a','verification_excerpt':'x','verification_reason':'reviewed'}]
        js=[]
        for j in roster:
            scores=dict(baseline['scores'][j]);scores['signal']=7
            js.append({'judge':j,'scores':scores,'as_of':'2026-11-16','reason':'review','lens_evidence':{k:(['e1'] if k=='signal' else []) for k in LENSES},'lens_reasons':dict.fromkeys(LENSES,'reason')})
        draft={'status':'draft','brand':'anthropic','baseline':baseline,'judgments':js,'evidence_sha256':mod.evidence_hash(evidence)}
        review={'evidence_review':'passed','judgments_sha256':mod.judgment_hash(js),'evidence_sha256':mod.evidence_hash(evidence),'reviews':[{'judge':j,'lens':'signal','verdict':'supported','reason':'ok'} for j in roster]}
        result=mod.build_draft(draft,review,baseline,evidence)
        self.assertIn('anthropic',result)
        self.assertIn('78/100',result)

class DraftContextTest(unittest.TestCase):
    def test_unchanged_draft_includes_evidence_and_discloses_no_change_review(self):
        from reaudit_judges import JUDGES,LENSES
        base={'version':'v4','scores':{j:dict.fromkeys(LENSES,8) for j in JUDGES}}
        evidence=[{'id':'e1','date':'2026-11-15','title':'Official announcement','verification':'verified','verification_source':'https://example.com/a','verification_excerpt':'example','verification_reason':'reviewed'}]
        judgments=[{'judge':j,'scores':dict(base['scores'][j]),'as_of':'2026-11-16','reason':'No material change','lens_evidence':{k:['e1'] for k in LENSES},'lens_reasons':dict.fromkeys(LENSES,'unchanged')} for j in JUDGES]
        draft={'status':'draft','brand':'apple','baseline':base,'judgments':judgments,'evidence_sha256':mod.evidence_hash(evidence)}
        review={'evidence_review':'passed','judgments_sha256':mod.judgment_hash(judgments),'evidence_sha256':mod.evidence_hash(evidence),'reviews':[]}
        result=mod.build_draft(draft,review,base,evidence)
        self.assertIn('Official announcement',result)
        self.assertIn('https://example.com/a',result)
        self.assertIn('未对维持不变的评分进行独立复核',result)
        self.assertIn('No material change',result)

class DisclosureTest(unittest.TestCase):
    def test_draft_preserves_original_conflict_markers_and_exclusions(self):
        from reaudit_judges import LENSES
        base={'version':'v1','scores':{'j':dict.fromkeys(LENSES,8)},'disclosures':{'j':'△'},'excluded_judges':['other']}
        evidence=[{'id':'e1','date':'2026-11-15','verification':'verified','verification_source':'https://example.com/a','verification_excerpt':'x','verification_reason':'reviewed'}]
        judgments=[{'judge':'j','scores':dict(base['scores']['j']),'as_of':'2026-11-16','reason':'unchanged','lens_evidence':{k:[] for k in LENSES},'lens_reasons':dict.fromkeys(LENSES,'unchanged')}]
        draft={'status':'draft','brand':'example','baseline':base,'judgments':judgments,'evidence_sha256':mod.evidence_hash(evidence)}
        review={'evidence_review':'passed','judgments_sha256':mod.judgment_hash(judgments),'evidence_sha256':mod.evidence_hash(evidence),'reviews':[]}
        result=mod.build_draft(draft,review,base,evidence)
        self.assertIn('j: △',result)
        self.assertIn('other',result)
