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
