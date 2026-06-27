import datetime as dt
import uuid

import pytest

from app.domain.chunk import RefusalContext, RetrievalResult, SearchResponse
from app.domain.document import DocumentFrontmatter


def test_document_frontmatter_construction():
    fm = DocumentFrontmatter(
        title="Reactor Manual",
        classification="restricted",
        department="engineering",
        version="2.3",
        effective_date=dt.date(2023, 8, 1),
        lineage_id="reactor-manual",
    )
    assert fm.title == "Reactor Manual"
    assert fm.classification == "restricted"


def test_document_frontmatter_rejects_invalid_classification():
    with pytest.raises(ValueError):
        DocumentFrontmatter(
            title="x",
            classification="alien",
            department="engineering",
            version="1.0",
            effective_date=dt.date(2020, 1, 1),
            lineage_id="x",
        )


def test_retrieval_result_required_fields():
    rr = RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="t",
        classification="public",
        department="hr",
        effective_date=dt.date(2020, 1, 1),
        snippet="...",
        score=0.5,
        rank=1,
    )
    assert rr.rank == 1


def test_refusal_context_holds_ref_id_and_withheld_ids():
    wid = uuid.uuid4()
    rc = RefusalContext(reference_id="A7F2-CXJK", withheld_count=1, withheld_ids=(wid,))
    assert rc.reference_id == "A7F2-CXJK"
    assert rc.withheld_ids == (wid,)


def test_search_response_optional_refusal_default_none():
    sr = SearchResponse(results=())
    assert sr.refusal is None
