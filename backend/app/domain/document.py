from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.core.clearance import CLEARANCE_RANK

VALID_CLASSIFICATIONS = frozenset(CLEARANCE_RANK)


@dataclass(frozen=True)
class DocumentFrontmatter:
    title: str
    classification: str
    department: str
    version: str
    effective_date: dt.date
    lineage_id: str

    def __post_init__(self) -> None:
        if self.classification not in VALID_CLASSIFICATIONS:
            raise ValueError(
                f"invalid classification {self.classification!r}; expected one of {sorted(VALID_CLASSIFICATIONS)}"
            )
        if not self.title.strip():
            raise ValueError("title must be non-empty")
        if not self.department.strip():
            raise ValueError("department must be non-empty")
        if not self.lineage_id.strip():
            raise ValueError("lineage_id must be non-empty")
