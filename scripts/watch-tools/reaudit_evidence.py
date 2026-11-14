#!/usr/bin/env python3
"""Prepare unconsumed watch leads for source verification, never for direct scoring."""
import argparse
import json
import re
from datetime import date, datetime
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import yaml


def prepare_events(events):
    result = []
    seen = set()
    for event in events:
        if event.get('consumed_by'):
            continue
        event_id = event.get('id')
        url = event.get('url', '')
        if not event_id or event_id in seen or not event.get('title') or urlparse(url).scheme not in ('http', 'https') or not urlparse(url).netloc:
            raise ValueError(f'invalid or duplicate event: {event_id}')
        seen.add(event_id)
        result.append({**event, 'verification': 'unverified'})
    return result


def assess_source(event, text):
    """A matching quotation confirms provenance only, never the truth of a claim."""
    normalize = lambda value: re.sub(r"\s+", " ", value).strip().casefold()
    quote = normalize(str(event.get("quote") or ""))
    return {"quote_match": bool(quote and quote in normalize(text)), "verification": "unverified"}


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.page_title = ''
        self.og_title = ''
        self.source_date = ''
        self.date_text = ''
        self.in_date = False
        self.in_title = False
        self.in_jsonld = False
        self.jsonld = []
        self.jsonld_buffer = ''
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'title':
            self.in_title = True
        if tag == 'script' and values.get('type') == 'application/ld+json':
            self.in_jsonld = True
            self.jsonld_buffer = ''
        if tag == 'span' and 'module_date-text' in (values.get('class') or '').split():
            self.in_date = True
        if tag == 'meta' and values.get('property') == 'og:title':
            self.og_title = values.get('content') or ''
        if tag == 'meta' and (values.get('property') in ('article:published_time', 'og:published_time') or values.get('name') in ('date', 'pubdate', 'publish-date')):
            self.source_date = (values.get('content') or '')[:10]
    def handle_endtag(self, tag):
        if tag == 'script' and self.in_jsonld:
            self.in_jsonld = False
            self.jsonld.append(self.jsonld_buffer)
        if tag == 'title':
            self.in_title = False
        if tag == 'span' and self.in_date:
            self.in_date = False
    def handle_data(self, data):
        self.parts.append(data)
        if self.in_title:
            self.page_title += data
        if self.in_date:
            self.date_text += data
        if self.in_jsonld:
            self.jsonld_buffer += data


OFFICIAL_HOSTS = {'nvidia': frozenset({'investor.nvidia.com', 'nvidianews.nvidia.com', 'blogs.nvidia.com', 'developer.nvidia.com'}), 'apple': frozenset({'www.apple.com'}), 'google': frozenset({'blog.google'})}
TRUSTED_SOURCE_HOSTS = frozenset().union(*OFFICIAL_HOSTS.values(), {'www.reuters.com', 'apnews.com'})


def allowed_source_url(url):
    try:
        parsed = urlparse(url)
        return (parsed.scheme == 'https' and parsed.hostname in TRUSTED_SOURCE_HOSTS
                and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443))
    except ValueError:
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_source(event):
    """Fetch a source for quote matching; a match is not fact verification."""
    try:
        if not allowed_source_url(event['url']):
            raise ValueError('source host is not allowlisted')
        req = urllib.request.Request(event['url'], headers={'User-Agent': 'MBA-Research/1.0'})
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(req, timeout=15) as response:
            data = response.read(1000001)
            if len(data) > 1000000:
                raise ValueError('response exceeds size limit')
            content_type = response.headers.get('Content-Type', '')
            if 'html' not in content_type and 'text/plain' not in content_type:
                raise ValueError('unsupported content type')
            text = data.decode('utf-8', errors='replace')
            if 'html' in content_type:
                parser = TextParser()
                parser.feed(text)
                if not parser.source_date:
                    found = set()
                    def visit(value):
                        if isinstance(value, dict):
                            if isinstance(value.get('datePublished'), str):
                                found.add(value['datePublished'][:10])
                            for child in value.values():
                                visit(child)
                        elif isinstance(value, list):
                            for child in value:
                                visit(child)
                    for block in parser.jsonld:
                        try:
                            visit(json.loads(block))
                        except (ValueError, RecursionError):
                            pass
                    if len(found) == 1:
                        parser.source_date = next(iter(found))
                if not parser.source_date and parser.date_text.strip():
                    try:
                        parser.source_date = datetime.strptime(parser.date_text.strip(), '%B %d, %Y').date().isoformat()
                    except ValueError:
                        pass
                text = ' '.join(parser.parts)
            return {**assess_source(event, text), 'fetch_status': 'ok', 'final_url': response.geturl(), 'source_date': parser.source_date if 'html' in content_type else '', 'source_title': (parser.og_title or parser.page_title) if 'html' in content_type else ''}
    except (OSError, ValueError, KeyError) as exc:
        return {'fetch_status': 'error', 'error': str(exc), 'quote_match': False, 'verification': 'unverified'}


NVIDIA_OFFICIAL_HOSTS = OFFICIAL_HOSTS['nvidia']


def official_statement_evidence(event, source, brand='nvidia'):
    """Confirm an attributable company statement, not its underlying factual truth."""
    url = event.get('url', '')
    parsed = urlparse(url)
    if (not allowed_source_url(url) or parsed.hostname not in OFFICIAL_HOSTS.get(brand, frozenset())
            or event.get('source_type') != 'official' or source.get('final_url') != url
            or source.get('fetch_status') != 'ok' or not source.get('quote_match')):
        raise ValueError('not an eligible direct company source')
    try:
        event_date = date.fromisoformat(str(event.get('date')))
        source_date = date.fromisoformat(source.get('source_date', ''))
    except ValueError:
        raise ValueError('invalid or missing publication date')
    if event_date != source_date:
        raise ValueError('event and source publication dates differ')
    quote = str(event.get('quote') or '').strip()
    title = str(source.get('source_title') or '').strip()
    if not quote or not title or quote.casefold() != title.casefold():
        raise ValueError('source title and quote differ')
    return {**event, 'verification': 'verified', 'verification_scope': 'official_statement',
            'verification_source': url, 'verification_excerpt': quote,
            'verification_reason': f'Exact dated title verified on {brand} official source; confirms publication only, not independent factual truth.',
            'verified_at': date.today().isoformat(), 'verification_by': 'automated-source-match'}


def validate_score_evidence(ids, evidence):
    """Reject scoring changes without explicitly verified, known evidence."""
    if not ids:
        raise ValueError("score change requires evidence")
    by_id = {item["id"]: item for item in evidence}
    if len(by_id) != len(evidence):
        raise ValueError("duplicate evidence IDs")
    for event_id in ids:
        if event_id not in by_id or by_id[event_id].get("verification") != "verified":
            raise ValueError(f"missing or unverified evidence: {event_id}")
        item = by_id[event_id]
        source = urlparse(str(item.get("verification_source") or ""))
        if source.scheme not in ("http", "https") or not source.netloc or not str(item.get("verification_excerpt") or "").strip() or not str(item.get("verification_reason") or "").strip():
            raise ValueError(f"verified evidence lacks source, excerpt, or reason: {event_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('events', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fetch-limit', type=int, default=0, help='fetch at most this many sources')
    parser.add_argument('--after', help='select events after an ISO date, including same-day additions with a snapshot')
    parser.add_argument('--baseline-events', type=Path)
    parser.add_argument('--auto-official', action='store_true', help='record matching dated company statements as attributed evidence')
    parser.add_argument('--brand', choices=sorted(OFFICIAL_HOSTS), default='nvidia')
    args = parser.parse_args()
    events = yaml.safe_load(args.events.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events must be a list')
    result = prepare_events(events)
    if args.fetch_limit < 0:
        parser.error("--fetch-limit must be nonnegative")
    if args.after:
        cutoff = date.fromisoformat(args.after)
        baseline_events = yaml.safe_load(args.baseline_events.read_text(encoding='utf-8')) if args.baseline_events else None
        if baseline_events is not None and (not isinstance(baseline_events, list) or any(not isinstance(e, dict) or not e.get('id') for e in baseline_events)):
            raise ValueError('invalid baseline event snapshot')
        ids = {e['id'] for e in baseline_events} if baseline_events is not None else None
        result = [event for event in result if date.fromisoformat(str(event['date'])) > cutoff or (ids is not None and date.fromisoformat(str(event['date'])) == cutoff and event['id'] not in ids)]
    if args.auto_official and any(not allowed_source_url(event['url']) for event in result):
        import reaudit_feed
        entries = reaudit_feed.fetch_feeds(args.brand)
        for event in result:
            if not allowed_source_url(event['url']):
                matched = reaudit_feed.match_official(event, entries, args.brand)
                if matched:
                    event.update(matched)
    candidates = [event for event in result if allowed_source_url(event['url'])]
    for event in candidates[:args.fetch_limit]:
        fetched = fetch_source(event)
        event.update(fetched)
        if args.auto_official:
            try:
                event.update(official_statement_evidence(event, fetched, args.brand))
            except ValueError:
                pass
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    verified = sum(item.get('verification') == 'verified' for item in result)
    print(f'{len(result)} leads ({verified} attributed official statements) written to {args.output}')

if __name__ == '__main__':
    main()
