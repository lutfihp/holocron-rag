from __future__ import annotations

import pytest

from app.services.ingestion.entity_extractor import extract_entities


@pytest.mark.slow
def test_real_spacy_extracts_meaningful_entities():
    text = (
        "All Death Star personnel must complete the quarterly audit cadence review "
        "by 2023-12-15. Incident response procedures fall under Security oversight."
    )
    ents = extract_entities(text)
    assert any("audit" in e for e in ents)
    assert any("incident" in e for e in ents)
    assert any("death star" in e for e in ents)
