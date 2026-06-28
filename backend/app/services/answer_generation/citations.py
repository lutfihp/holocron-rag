from __future__ import annotations

import re

_MARKER_RE = re.compile(r"\[(\d+)\]")


def parse_citation_markers(text: str, *, total_chunks: int) -> list[int]:
    if total_chunks <= 0:
        return []
    found = sorted({int(m) for m in _MARKER_RE.findall(text)})
    return [i for i in found if 1 <= i <= total_chunks]
