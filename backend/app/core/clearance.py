from __future__ import annotations

import uuid
from dataclasses import dataclass

CLEARANCE_RANK: dict[str, int] = {
    "public": 0,
    "restricted": 1,
    "secret": 2,
    "top_secret": 3,
}


def allowed_levels(max_clearance: str) -> list[str]:
    """Return all classification labels at or below the user's clearance."""
    max_rank = CLEARANCE_RANK[max_clearance]
    return [label for label, rank in CLEARANCE_RANK.items() if rank <= max_rank]


@dataclass(frozen=True)
class ClearanceContext:
    """Immutable RBAC context required by every chunk read.

    Holding a ClearanceContext is a type-level proof that the caller has
    presented the user's clearance + departments. There is no public chunk
    read API that does not take one.
    """

    tenant_id: uuid.UUID
    user_id: uuid.UUID
    max_clearance: str
    departments: tuple[str, ...]
