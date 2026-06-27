from __future__ import annotations

import secrets
import uuid
from typing import Sequence

from app.repositories.audit_repository import AuditRepository

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # Crockford-ish base32, no 0/1/8/9


def generate_reference_id() -> str:
    """Eight base32 chars in two hyphenated groups, e.g. 'A7F2-CXJK'."""
    chars = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"{chars[:4]}-{chars[4:]}"


async def record_refusal(
    audit: AuditRepository,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    retrieved_ids: Sequence[uuid.UUID],
    withheld_ids: Sequence[uuid.UUID],
) -> str:
    ref = generate_reference_id()
    await audit.insert_refusal(
        tenant_id=tenant_id,
        user_id=user_id,
        reference_id=ref,
        retrieved_ids=retrieved_ids,
        withheld_ids=withheld_ids,
    )
    return ref
