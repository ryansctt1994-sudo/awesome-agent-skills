#!/usr/bin/env python3
"""Offline URL hygiene; optional bounded live checks for curated Markdown catalogs."""
import argparse
import concurrent.futures
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

URL_RE = re.compile(r'https?://[^\s<>\]\[\)"\']+')


def extract_urls(markdown: str):
    return sorted(set(URL_RE.findall(markdown)))


def validate_url(url: str):
    parts = urlsplit(url)
    return bool(parts.scheme in ('http', 'https') and parts.hostname and not any(c.isspace() for c in url))


def live_check(url: str):
    try:
        request = Request(url, headers={'User-Agent': 'TinkerforgeLinkAudit/1.0'}, method='HEAD')
        with urlopen(request, timeout=8) as r:
            return ('ok', r.status)
    except HTTPError as e:
        if e.code in (405, 501):
            try:
                with urlopen(Request(url, headers={'User-Agent': 'TinkerforgeLinkAudit/1.0', 'Range': 'bytes=0-0'}), timeout=8) as r:
                    return ('ok', r.status)
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                return ('unknown', str(exc))
        if e.code in (404, 410):
            return ('broken', e.code)
        return ('unknown', e.code)
    except (URLError, TimeoutError, OSError) as e:
        return ('unknown', str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('markdown', type=Path)
    parser.add_argument('--live', action='store_true', help='Make external network requests (never default)')
    args = parser.parse_args()
    urls = extract_urls(args.markdown.read_text(encoding='utf-8'))
    invalid = [url for url in urls if not validate_url(url)]
    print(f'Extracted {len(urls)} distinct HTTP(S) links; {len(invalid)} malformed')
    for url in invalid:
        print('MALFORMED', url)
    if invalid:
        return 1
    if args.live:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(live_check, urls))
        counts = {s: sum(r[0] == s for r in results) for s in ('ok', 'broken', 'unknown')}
        print('Live check:', counts)
        for url, result in zip(urls, results):
            if result[0] == 'broken':
                print('BROKEN', url, result[1])
        return 1 if counts['broken'] else 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
