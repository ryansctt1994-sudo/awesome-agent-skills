#!/usr/bin/env python3
"""Check local README fragment links without network requests or third-party deps."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


def heading_slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).casefold()
    text = re.sub(r"[^\w\- ]", "", text)
    return re.sub(r"\s+", "-", text.strip())


def anchors(markdown: str) -> set[str]:
    explicit = set(re.findall(r'<a\b[^>]*\b(?:name|id)=["\x27]([^"\x27]+)["\x27]', markdown, re.I))
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", markdown, re.M):
        slug = heading_slug(heading)
        if slug:
            n = counts.get(slug, 0)
            counts[slug] = n + 1
            explicit.add(slug if n == 0 else f"{slug}-{n}")
    return explicit


def unresolved_fragments(markdown: str) -> list[str]:
    known = anchors(markdown)
    links = [unquote(m) for m in re.findall(r"\]\(#([^\)]+)\)", markdown)]
    return sorted(set(links) - known)


def main() -> int:
    file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "README.md"
    missing = unresolved_fragments(file.read_text(encoding="utf-8"))
    if missing:
        print(f"FAIL: {len(missing)} missing README fragment target(s):")
        for fragment in missing:
            print(f"  #{fragment}")
        return 1
    print("PASS: all README fragment links have corresponding anchors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
