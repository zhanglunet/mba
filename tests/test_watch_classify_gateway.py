import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('watch_classifier', Path(__file__).resolve().parents[1] / 'scripts/watch-tools/classify_candidates.py')
classifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classifier)

class GatewayTest(unittest.TestCase):
    def test_glm_coding_disables_thinking_and_classifies(self):
        captured = {}
        def respond(req, timeout):
            captured.update(json.loads(req.data))
            return io.BytesIO(json.dumps({'choices': [{'message': {'content': '[{"keep": true}]'}, 'finish_reason': 'stop'}]}).encode())
        with patch.object(classifier.urllib.request, 'urlopen', respond):
            result = classifier.call_llm([{'title': 'news'}], ('openai', 'key', 'https://open.bigmodel.cn/api/coding/paas/v4', 'glm-5.3'))
        self.assertEqual(result, [{'keep': True}])
        self.assertEqual(captured['thinking'], {'type': 'disabled'})

    def test_truncated_response_reports_finish_reason(self):
        def respond(req, timeout):
            return io.BytesIO(json.dumps({'choices': [{'message': {'content': ''}, 'finish_reason': 'length'}]}).encode())
        with patch.object(classifier.urllib.request, 'urlopen', respond):
            with self.assertRaisesRegex(ValueError, 'finish_reason=length'):
                classifier.call_llm([], ('openai', 'key', 'https://example.com/v1', 'model'))

if __name__ == '__main__':
    unittest.main()
