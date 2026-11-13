import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'scripts/watch-tools/reaudit_evidence.py'
spec = importlib.util.spec_from_file_location('reaudit_evidence', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class EvidenceTest(unittest.TestCase):
    def test_unconsumed_events_remain_unverified(self):
        events = [{'id': 'old', 'consumed_by': 'v3'}, {'id': 'new', 'title': 'Title', 'url': 'https://example.com/a', 'severity': 'P1'}]
        selected = module.prepare_events(events)
        self.assertEqual([e['id'] for e in selected], ['new'])
        self.assertEqual(selected[0]['verification'], 'unverified')

    def test_missing_source_is_rejected(self):
        with self.assertRaises(ValueError):
            module.prepare_events([{'id': 'a', 'title': 'Title'}])

class SourceTest(unittest.TestCase):
    def test_title_matching_does_not_mark_fact_verified(self):
        result = module.assess_source({'quote': 'NVIDIA launches new platform'}, 'NVIDIA launches new platform')
        self.assertEqual(result['quote_match'], True)
        self.assertEqual(result['verification'], 'unverified')

    def test_missing_quote_is_not_a_match(self):
        result = module.assess_source({'quote': ''}, 'Some content')
        self.assertEqual(result['quote_match'], False)

class GateTest(unittest.TestCase):
    def test_unverified_claim_cannot_support_score(self):
        with self.assertRaisesRegex(ValueError, 'unverified'):
            module.validate_score_evidence(['evt-1'], [{'id': 'evt-1', 'verification': 'unverified'}])

    def test_missing_claim_cannot_support_score(self):
        with self.assertRaises(ValueError):
            module.validate_score_evidence(['missing'], [])

    def test_verified_claim_can_support_score(self):
        module.validate_score_evidence(['evt-1'], [{'id': 'evt-1', 'verification': 'verified', 'verification_source': 'https://example.com/source', 'verification_excerpt': 'evidence', 'verification_reason': 'reviewed'}])

class FetchTest(unittest.TestCase):
    def test_source_fetch_records_match_without_verifying_claim(self):
        from unittest.mock import patch
        class Response:
            headers = {'Content-Type': 'text/html; charset=utf-8'}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return b'<html><title>Important news</title><body>Important news</body></html>'
            def geturl(self): return 'https://example.com/article'
        with patch.object(module.urllib.request, 'urlopen', return_value=Response()):
            result = module.fetch_source({'url': 'https://example.com/article', 'quote': 'Important news'})
        self.assertTrue(result['quote_match'])
        self.assertEqual(result['verification'], 'unverified')
        self.assertEqual(result['fetch_status'], 'ok')

    def test_source_failure_stays_unverified(self):
        from unittest.mock import patch
        with patch.object(module.urllib.request, 'urlopen', side_effect=OSError('offline')):
            result = module.fetch_source({'url': 'https://example.com/article', 'quote': 'x'})
        self.assertEqual(result['fetch_status'], 'error')
        self.assertEqual(result['verification'], 'unverified')

class ProvenanceTest(unittest.TestCase):
    def test_verified_flag_without_provenance_is_rejected(self):
        with self.assertRaises(ValueError):
            module.validate_score_evidence(['e1'], [{'id': 'e1', 'verification': 'verified'}])

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            module.validate_score_evidence(['e1'], [{'id': 'e1'}, {'id': 'e1'}])
