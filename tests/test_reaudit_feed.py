import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/watch-tools'))
import reaudit_feed as mod

class FeedTest(unittest.TestCase):
    def test_maps_matching_headline_and_date_to_official_url(self):
        xml=b'<rss><channel><item><title>Launch</title><link>https://blogs.nvidia.com/blog/launch/</link><pubDate>Sun, 15 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>'
        feed=mod.parse_feed(xml)
        event={'id':'e1','date':'2026-11-15','quote':'Launch','url':'https://news.google.com/article','source_type':'official'}
        result=mod.match_official(event,feed)
        self.assertEqual(result['url'],'https://blogs.nvidia.com/blog/launch/')
        self.assertEqual(result['original_url'],event['url'])
    def test_ambiguous_or_date_mismatched_matches_are_not_used(self):
        feed=[{'title':'Launch','date':'2026-11-15','url':'https://blogs.nvidia.com/a'}, {'title':'Launch','date':'2026-11-15','url':'https://blogs.nvidia.com/b'}]
        event={'id':'e1','date':'2026-11-15','quote':'Launch','url':'https://news.google.com/a'}
        self.assertIsNone(mod.match_official(event,feed))
        event['date']='2026-11-14'
        self.assertIsNone(mod.match_official(event,feed))
