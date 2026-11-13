#!/usr/bin/env python3
"""Offline relative Markdown-link and GitHub-style heading-anchor audit.

No HTTP traffic. Handles Markdown headings, HTML h1-h6 (including <summary>),
explicit <a id/name>, URL-escaped fragments, and duplicate heading slugs.
"""
from __future__ import annotations

import argparse
import html
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)]+)\)')
HEADING = re.compile(r'^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$')
HTML_HEADING = re.compile(r'<h[1-6]\b[^>]*>(.*?)</h[1-6]>', re.I)
EXPLICIT = re.compile(r'<a\b[^>]*\b(?:id|name)\s*=\s*["\']([^"\']+)["\']', re.I)
FENCE = re.compile(r'^\s*(`{3,}|~{3,})')


def slug(text: str) -> str:
    text = html.unescape(re.sub(r'<[^>]+>', '', text)).strip().lower()
    text = text.replace(' ', '-')
    return ''.join(ch for ch in text if ch in '-_' or ch.isalnum() or ch.isspace())


def anchors(text: str) -> set[str]:
    known: set[str] = set()
    counts: dict[str, int] = {}
    fence = None
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker[0]
            elif fence == marker[0]:
                fence = None
            continue
        if fence:
            continue
        for raw in [*( [m.group(1) for m in HTML_HEADING.finditer(line)] ),
                    *( [m.group(1) for m in [HEADING.match(line)] if m] )]:
            base = slug(re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', raw))
            if not base:
                continue
            index = counts.get(base, 0)
            known.add(base if index == 0 else f'{base}-{index}')
            counts[base] = index + 1
        known.update(html.unescape(m.group(1)) for m in EXPLICIT.finditer(line))
    return known


def scan(root: Path) -> list[str]:
    root = root.resolve()
    errors = []
    cache: dict[Path, set[str]] = {}
    files = sorted(root.rglob('*.md'))
    for source in files:
        contents = source.read_text(encoding='utf-8')
        fence = None
        for number, line in enumerate(contents.splitlines(), 1):
            match = FENCE.match(line)
            if match:
                marker = match.group(1)[0]
                if fence is None:
                    fence = marker
                elif fence == marker:
                    fence = None
                continue
            if fence:
                continue
            for link in LINK.findall(line):
                target_link = link.strip().split(' "', 1)[0]
                parsed = urlsplit(target_link)
                if parsed.scheme or parsed.netloc or target_link.startswith('//'):
                    continue
                rel = unquote(parsed.path)
                fragment = unquote(parsed.fragment)
                target = (source.parent / rel).resolve() if rel else source.resolve()
                if not target.is_relative_to(root):
                    errors.append(f'{source.relative_to(root)}:{number}: path escapes repository: {target_link}')
                    continue
                if not target.is_file():
                    errors.append(f'{source.relative_to(root)}:{number}: missing target: {target_link}')
                    continue
                if fragment and target.suffix.lower() == '.md':
                    if target not in cache:
                        cache[target] = anchors(target.read_text(encoding='utf-8'))
                    if fragment not in cache[target]:
                        errors.append(f'{source.relative_to(root)}:{number}: missing anchor: {target_link}')
    print(f'Checked {len(files)} Markdown files, {len(errors)} internal-link errors')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path, nargs='?', default=Path('.'))
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error('root must be a directory')
    errors = scan(args.root)
    for error in errors:
        print('FAIL', error)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
