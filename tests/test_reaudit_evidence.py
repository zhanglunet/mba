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
        with patch.object(module.urllib.request, 'build_opener') as factory:
            factory.return_value.open.return_value = Response()
            result = module.fetch_source({'url': 'https://investor.nvidia.com/article', 'quote': 'Important news'})
        self.assertTrue(result['quote_match'])
        self.assertEqual(result['verification'], 'unverified')
        self.assertEqual(result['fetch_status'], 'ok')

    def test_source_failure_stays_unverified(self):
        from unittest.mock import patch
        with patch.object(module.urllib.request, 'build_opener') as factory:
            factory.return_value.open.side_effect = OSError('offline')
            result = module.fetch_source({'url': 'https://investor.nvidia.com/article', 'quote': 'x'})
        self.assertEqual(result['fetch_status'], 'error')
        self.assertEqual(result['verification'], 'unverified')

class ProvenanceTest(unittest.TestCase):
    def test_verified_flag_without_provenance_is_rejected(self):
        with self.assertRaises(ValueError):
            module.validate_score_evidence(['e1'], [{'id': 'e1', 'verification': 'verified'}])

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            module.validate_score_evidence(['e1'], [{'id': 'e1'}, {'id': 'e1'}])

class PublicSourceTest(unittest.TestCase):
    def test_rejects_local_and_private_addresses(self):
        for url in ['http://127.0.0.1/', 'https://localhost/', 'http://169.254.169.254/', 'http://[::1]/']:
            with self.subTest(url=url):
                self.assertFalse(module.allowed_source_url(url))

    def test_allows_only_explicit_trusted_domains(self):
        self.assertTrue(module.allowed_source_url('https://investor.nvidia.com/news/press'))
        self.assertFalse(module.allowed_source_url('https://investor.nvidia.com.attacker.example/news'))
        self.assertFalse(module.allowed_source_url('https://user:pass@investor.nvidia.com/news'))

class OfficialEvidenceTest(unittest.TestCase):
    def test_exact_official_title_and_date_can_support_attributed_statement(self):
        event={'id':'e1','title':'Launch','quote':'Launch','date':'2026-11-15','url':'https://blogs.nvidia.com/blog/launch/','source_type':'official'}
        source={'fetch_status':'ok','quote_match':True,'source_date':'2026-11-15','source_title':'Launch','final_url':event['url']}
        result=module.official_statement_evidence(event, source)
        self.assertEqual(result['verification'],'verified')
        self.assertEqual(result['verification_scope'],'official_statement')

    def test_mismatched_date_or_source_cannot_be_promoted(self):
        event={'id':'e1','title':'Launch','quote':'Launch','date':'2026-11-15','url':'https://blogs.nvidia.com/blog/launch/','source_type':'official'}
        for source in [{'fetch_status':'ok','quote_match':True,'source_date':'2026-11-14','final_url':event['url']}, {'fetch_status':'ok','quote_match':True,'source_date':'2026-11-15','final_url':'https://www.reuters.com/a'}]:
            with self.assertRaises(ValueError): module.official_statement_evidence(event, source)

class OfficialPipelineTest(unittest.TestCase):
    def test_html_metadata_passes_to_attributed_evidence(self):
        from unittest.mock import patch
        class Response:
            headers={'Content-Type':'text/html; charset=utf-8'}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n): return b'<html><head><title>Launch</title><meta property="article:published_time" content="2026-11-15T12:00:00Z"></head><body>Launch</body></html>'
            def geturl(self): return 'https://blogs.nvidia.com/blog/launch/'
        event={'id':'e1','title':'Launch','quote':'Launch','date':'2026-11-15','url':'https://blogs.nvidia.com/blog/launch/','source_type':'official'}
        with patch.object(module.urllib.request,'build_opener') as factory:
            factory.return_value.open.return_value=Response()
            source=module.fetch_source(event)
        self.assertEqual(module.official_statement_evidence(event,source)['verification_scope'],'official_statement')
