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

class AppleFeedTest(unittest.TestCase):
    def test_apple_atom_entry_has_direct_official_url(self):
        xml=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Apple Launch</title><updated>2026-11-13T12:00:00Z</updated><link href="https://www.apple.com/newsroom/2026/11/launch/"/></entry></feed>'
        feed=mod.parse_feed(xml,brand='apple')
        self.assertEqual(feed[0]['date'],'2026-11-13')
        result=mod.match_official({'id':'a','quote':'Apple Launch','date':'2026-11-13','url':'https://news.google.com/a'},feed,brand='apple')
        self.assertEqual(result['url'],'https://www.apple.com/newsroom/2026/11/launch/')

class AmazonFeedTest(unittest.TestCase):
    def test_amazon_official_feed_profile_is_isolated(self):
        xml=b'<rss><channel><item><title>Amazon Launch</title><link>https://www.aboutamazon.com/news/example</link><pubDate>Wed, 11 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        feed=mod.parse_feed(xml,brand='amazon')
        event={'id':'a','quote':'Amazon Launch','date':'2026-11-11','url':'https://news.google.com/a'}
        self.assertEqual(mod.match_official(event,feed,brand='amazon')['url'],'https://www.aboutamazon.com/news/example')
        self.assertIsNone(mod.match_official(event,feed,brand='apple'))
