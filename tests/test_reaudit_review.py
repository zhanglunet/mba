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
