from __future__ import annotations

import uuid

from app.services.answer_generation.citations import parse_citation_markers


def test_finds_markers_in_text():
    text = "Foo [1] and bar [2], also [1] again."
    assert parse_citation_markers(text, total_chunks=3) == [1, 2]


def test_drops_out_of_range_markers():
    text = "Foo [1] bar [99]."
    assert parse_citation_markers(text, total_chunks=2) == [1]


def test_returns_empty_for_no_markers():
    assert parse_citation_markers("nothing cited here", total_chunks=5) == []


def test_returns_empty_for_zero_chunks():
    assert parse_citation_markers("[1] [2]", total_chunks=0) == []
