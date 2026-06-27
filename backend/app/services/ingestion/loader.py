from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import frontmatter

from app.domain.document import DocumentFrontmatter


@dataclass(frozen=True)
class LoadedDocument:
    frontmatter: DocumentFrontmatter
    body: str
    source_uri: str  # posix path relative to corpus_root.parent, e.g. 'corpus/hr/handbook.md'


REQUIRED_KEYS = ("title", "classification", "department", "version", "effective_date", "lineage_id")


def load_one(path: Path, *, corpus_root: Path) -> LoadedDocument:
    post = frontmatter.load(path)
    if not post.metadata or "title" not in post.metadata:
        raise ValueError(f"missing frontmatter in {path}")
    missing = [k for k in REQUIRED_KEYS if k not in post.metadata]
    if missing:
        raise ValueError(f"frontmatter in {path} missing required keys: {missing}")

    eff = post.metadata["effective_date"]
    if isinstance(eff, str):
        eff = dt.date.fromisoformat(eff)
    elif isinstance(eff, dt.datetime):
        eff = eff.date()
    elif not isinstance(eff, dt.date):
        raise ValueError(f"effective_date in {path} must be a date, got {type(eff).__name__}")

    fm = DocumentFrontmatter(
        title=str(post.metadata["title"]).strip(),
        classification=str(post.metadata["classification"]).strip(),
        department=str(post.metadata["department"]).strip(),
        version=str(post.metadata["version"]).strip(),
        effective_date=eff,
        lineage_id=str(post.metadata["lineage_id"]).strip(),
    )

    # build the source_uri relative to corpus_root's parent so 'corpus/...' is preserved
    try:
        rel = path.resolve().relative_to(corpus_root.resolve().parent).as_posix()
    except ValueError:
        rel = path.as_posix()

    return LoadedDocument(frontmatter=fm, body=post.content, source_uri=rel)


def load_corpus_dir(root: Path) -> list[LoadedDocument]:
    """Recursively load every *.md file under root. Fails loud on any invalid frontmatter."""
    out: list[LoadedDocument] = []
    for p in sorted(root.rglob("*.md")):
        out.append(load_one(p, corpus_root=root))
    return out
