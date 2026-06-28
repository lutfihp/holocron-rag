from __future__ import annotations

from app.services.ingestion.entity_extractor import (
    extract_entities,
    _extract_from_doc,  # noqa: F401  helper used in test below
)


class _FakeToken:
    def __init__(self, lemma_: str, is_stop: bool = False, is_punct: bool = False) -> None:
        self.lemma_ = lemma_
        self.is_stop = is_stop
        self.is_punct = is_punct


class _FakeChunk:
    def __init__(self, tokens: list[_FakeToken], text: str) -> None:
        self.tokens = tokens
        self._text = text

    def __iter__(self):
        return iter(self.tokens)

    @property
    def text(self) -> str:
        return self._text


class _FakeEnt:
    def __init__(self, text: str, label_: str) -> None:
        self.text = text
        self.label_ = label_


class _FakeDoc:
    def __init__(self, noun_chunks: list[_FakeChunk], ents: list[_FakeEnt]) -> None:
        self.noun_chunks = noun_chunks
        self.ents = ents


def test_extracts_lemma_lower_noun_chunks_dedup():
    doc = _FakeDoc(
        noun_chunks=[
            _FakeChunk(
                [_FakeToken("audit"), _FakeToken("cadence")],
                "Audit Cadence",
            ),
            _FakeChunk(
                [_FakeToken("Audit"), _FakeToken("cadence")],
                "audit cadence",
            ),
            _FakeChunk(
                [_FakeToken("the", is_stop=True), _FakeToken("incident")],
                "the incident",
            ),
        ],
        ents=[_FakeEnt("Death Star", "ORG"), _FakeEnt("2023", "DATE")],
    )
    out = _extract_from_doc(doc)
    # Duplicates collapsed, stop-words dropped, NER preserved verbatim-lowered
    assert "audit cadence" in out
    assert "incident" in out
    assert "death star" in out
    assert "2023" in out
    # No duplicates
    assert len(out) == len(set(out))


def test_empty_text_returns_empty_tuple(monkeypatch):
    import app.services.ingestion.entity_extractor as ee

    def fake_loader():
        class _NL:
            def __call__(self, _text):
                return _FakeDoc(noun_chunks=[], ents=[])
        return _NL()

    monkeypatch.setattr(ee, "_load_spacy", fake_loader)
    monkeypatch.setattr(ee, "_nlp", None)  # force reload
    out = extract_entities("   ")
    assert out == ()
