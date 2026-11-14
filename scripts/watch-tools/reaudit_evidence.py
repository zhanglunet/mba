#!/usr/bin/env python3
"""Prepare unconsumed watch leads for source verification, never for direct scoring."""
import argparse
import json
import re
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
    def handle_data(self, data):
        self.parts.append(data)


TRUSTED_SOURCE_HOSTS = frozenset({'investor.nvidia.com', 'nvidianews.nvidia.com', 'blogs.nvidia.com', 'developer.nvidia.com', 'www.reuters.com', 'apnews.com'})


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
                text = ' '.join(parser.parts)
            return {**assess_source(event, text), 'fetch_status': 'ok', 'final_url': response.geturl()}
    except (OSError, ValueError, KeyError) as exc:
        return {'fetch_status': 'error', 'error': str(exc), 'quote_match': False, 'verification': 'unverified'}


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
    args = parser.parse_args()
    events = yaml.safe_load(args.events.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events must be a list')
    result = prepare_events(events)
    if args.fetch_limit < 0:
        parser.error("--fetch-limit must be nonnegative")
    for event in result[:args.fetch_limit]:
        event.update(fetch_source(event))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    print(f'{len(result)} unverified leads written to {args.output}')

if __name__ == '__main__':
    main()
