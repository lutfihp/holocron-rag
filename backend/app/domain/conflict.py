from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    marker: int
    chunk_id: uuid.UUID
    text: str


@dataclass(frozen=True)
class ConflictPair:
    """A candidate pair surfaced by the heuristic prefilter, before judging."""

    chunk_a_id: uuid.UUID
    chunk_b_id: uuid.UUID
    a_rank: int
    b_rank: int

    def canonical_key(self) -> tuple[uuid.UUID, uuid.UUID]:
        lo, hi = sorted((self.chunk_a_id, self.chunk_b_id))
        return (lo, hi)

    def rank_sum(self) -> int:
        return self.a_rank + self.b_rank


@dataclass(frozen=True)
class Conflict:
    subject: str
    position_a: Position
    position_b: Position
