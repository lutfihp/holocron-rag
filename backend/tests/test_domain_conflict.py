from __future__ import annotations

import uuid

from app.domain.conflict import Conflict, ConflictPair, Position


def test_conflict_pair_is_hashable_and_orderless():
    a = uuid.uuid4()
    b = uuid.uuid4()
    p1 = ConflictPair(chunk_a_id=a, chunk_b_id=b, a_rank=1, b_rank=2)
    p2 = ConflictPair(chunk_a_id=b, chunk_b_id=a, a_rank=2, b_rank=1)
    # Same underlying pair must produce the same canonical key
    assert p1.canonical_key() == p2.canonical_key()
    assert p1.rank_sum() == 3
    assert p2.rank_sum() == 3


def test_conflict_payload_immutable():
    cid_a = uuid.uuid4()
    cid_b = uuid.uuid4()
    c = Conflict(
        subject="Off-duty unit insignia",
        position_a=Position(marker=1, chunk_id=cid_a, text="A says..."),
        position_b=Position(marker=2, chunk_id=cid_b, text="B says..."),
    )
    assert c.subject == "Off-duty unit insignia"
    assert c.position_a.marker == 1
    assert c.position_b.text == "B says..."
