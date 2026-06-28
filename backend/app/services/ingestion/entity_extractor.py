from __future__ import annotations

from typing import Any

_MODEL_NAME = "en_core_web_sm"
_nlp: Any | None = None


def _load_spacy() -> Any:
    import spacy  # heavy import; defer

    # Full default pipeline: tok2vec, tagger, parser, attribute_ruler, lemmatizer, ner.
    # All are required: parser for noun_chunks, lemmatizer for token.lemma_, ner for entities.
    return spacy.load(_MODEL_NAME)


def get_default_extractor() -> Any:
    """Cached singleton — spaCy model loads once per process."""
    global _nlp
    if _nlp is None:
        _nlp = _load_spacy()
    return _nlp


def _extract_from_doc(doc: Any) -> tuple[str, ...]:
    seen: list[str] = []
    seen_set: set[str] = set()

    def add(term: str) -> None:
        t = term.strip().lower()
        if not t:
            return
        if t in seen_set:
            return
        seen_set.add(t)
        seen.append(t)

    # Noun chunks: drop stop/punct tokens; join remaining token lemmas
    for chunk in doc.noun_chunks:
        toks = [tok.lemma_.lower() for tok in chunk if not tok.is_stop and not tok.is_punct]
        if toks:
            add(" ".join(toks))

    # Named entities: keep verbatim (lowered)
    for ent in doc.ents:
        add(ent.text)

    return tuple(seen)


def extract_entities(text: str) -> tuple[str, ...]:
    if not text or not text.strip():
        return ()
    nlp = get_default_extractor()
    doc = nlp(text)
    return _extract_from_doc(doc)
