#!/usr/bin/env python3
"""Match watch headlines to direct NVIDIA RSS links without guessing."""
import email.utils
import re
import urllib.request
import xml.etree.ElementTree as ET
from reaudit_evidence import NoRedirect, allowed_source_url, OFFICIAL_HOSTS
from urllib.parse import urlparse

FEEDS = {'nvidia': ('https://nvidianews.nvidia.com/rss.xml', 'https://blogs.nvidia.com/feed/'), 'apple': ('https://www.apple.com/newsroom/rss-feed.rss',), 'amazon': ('https://www.aboutamazon.com/rss/feed.rss',)}
MAX_FEED_BYTES = 1000000


def normalize(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip().casefold()


def parse_feed(data, brand='nvidia'):
    if len(data) > MAX_FEED_BYTES:
        raise ValueError('feed too large')
    root = ET.fromstring(data)
    result = []
    for item in root.findall('./channel/item'):
        title=(item.findtext('title') or '').strip()
        url=(item.findtext('link') or '').strip()
        published=(item.findtext('pubDate') or '').strip()
        try:
            day=email.utils.parsedate_to_datetime(published).date().isoformat()
        except (ValueError, TypeError, IndexError):
            continue
        if title and allowed_source_url(url) and urlparse(url).hostname in OFFICIAL_HOSTS.get(brand, frozenset()):
            result.append({'title':title,'date':day,'url':url})
    atom = '{http://www.w3.org/2005/Atom}'
    for item in root.findall(atom + 'entry'):
        title = (item.findtext(atom + 'title') or '').strip()
        link = item.find(atom + 'link')
        url = (link.get('href') or '').strip() if link is not None else ''
        day = (item.findtext(atom + 'published') or item.findtext(atom + 'updated') or '')[:10]
        try:
            from datetime import date
            date.fromisoformat(day)
        except ValueError:
            continue
        if title and allowed_source_url(url) and urlparse(url).hostname in OFFICIAL_HOSTS.get(brand, frozenset()):
            result.append({'title': title, 'date': day, 'url': url})
    return result


def match_official(event, entries, brand='nvidia'):
    quote=normalize(event.get('quote'))
    if not quote:
        return None
    matches={entry['url'] for entry in entries if normalize(entry.get('title')) == quote and entry.get('date') == str(event.get('date')) and allowed_source_url(entry.get('url','')) and urlparse(entry['url']).hostname in OFFICIAL_HOSTS.get(brand, frozenset())}
    if len(matches) != 1:
        return None
    return {**event, 'original_url':event.get('url'), 'url':next(iter(matches)), 'source_type':'official'}


def fetch_feeds(brand='nvidia'):
    opener=urllib.request.build_opener(NoRedirect())
    entries=[]
    for url in FEEDS.get(brand, ()):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'MBA-Research/1.0'})
            with opener.open(req,timeout=15) as response:
                entries.extend(parse_feed(response.read(MAX_FEED_BYTES+1), brand))
        except (OSError, ValueError, ET.ParseError) as exc:
            print(f'::warning::Official feed unavailable: {url}: {exc}')
    return entries
