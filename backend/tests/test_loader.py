import datetime as dt
import textwrap
from pathlib import Path

import pytest

from app.services.ingestion.loader import LoadedDocument, load_corpus_dir, load_one


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def test_load_one_parses_frontmatter_and_body(tmp_path):
    p = _write(
        tmp_path,
        "hr/handbook.md",
        textwrap.dedent(
            """\
            ---
            title: Imperial Employee Handbook
            classification: public
            department: hr
            version: "1.0"
            effective_date: 2019-04-12
            lineage_id: employee-handbook
            ---
            # Body
            All Imperial personnel...
            """
        ),
    )
    loaded = load_one(p, corpus_root=tmp_path)
    assert isinstance(loaded, LoadedDocument)
    assert loaded.frontmatter.title == "Imperial Employee Handbook"
    assert loaded.frontmatter.classification == "public"
    assert loaded.frontmatter.effective_date == dt.date(2019, 4, 12)
    assert loaded.source_uri.endswith("hr/handbook.md")
    assert "All Imperial personnel" in loaded.body


def test_load_one_rejects_missing_frontmatter(tmp_path):
    p = _write(tmp_path, "broken.md", "no frontmatter at all\n")
    with pytest.raises(ValueError, match="frontmatter"):
        load_one(p, corpus_root=tmp_path)


def test_load_one_rejects_invalid_classification(tmp_path):
    p = _write(
        tmp_path,
        "broken.md",
        textwrap.dedent(
            """\
            ---
            title: x
            classification: alien
            department: hr
            version: "1.0"
            effective_date: 2019-04-12
            lineage_id: x
            ---
            body
            """
        ),
    )
    with pytest.raises(ValueError, match="classification"):
        load_one(p, corpus_root=tmp_path)


def test_load_corpus_dir_loads_all_markdown(tmp_path):
    for rel in ["hr/a.md", "engineering/b.md", "engineering/c.md"]:
        _write(
            tmp_path,
            rel,
            textwrap.dedent(
                f"""\
                ---
                title: {rel}
                classification: public
                department: hr
                version: "1"
                effective_date: 2020-01-01
                lineage_id: {rel}
                ---
                body
                """
            ),
        )
    docs = load_corpus_dir(tmp_path)
    assert len(docs) == 3


def test_load_corpus_dir_skips_non_markdown(tmp_path):
    _write(tmp_path, "README.txt", "ignored")
    _write(
        tmp_path,
        "hr/a.md",
        textwrap.dedent(
            """\
            ---
            title: t
            classification: public
            department: hr
            version: "1"
            effective_date: 2020-01-01
            lineage_id: t
            ---
            body
            """
        ),
    )
    docs = load_corpus_dir(tmp_path)
    assert len(docs) == 1
