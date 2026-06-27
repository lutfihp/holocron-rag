import uuid

import pytest

from app.core.clearance import CLEARANCE_RANK, ClearanceContext, allowed_levels


def test_clearance_rank_total_order():
    assert CLEARANCE_RANK["public"] < CLEARANCE_RANK["restricted"]
    assert CLEARANCE_RANK["restricted"] < CLEARANCE_RANK["secret"]
    assert CLEARANCE_RANK["secret"] < CLEARANCE_RANK["top_secret"]


def test_allowed_levels_employee_sees_only_public():
    assert set(allowed_levels("public")) == {"public"}


def test_allowed_levels_manager_sees_public_and_restricted():
    assert set(allowed_levels("restricted")) == {"public", "restricted"}


def test_allowed_levels_director_sees_through_secret():
    assert set(allowed_levels("secret")) == {"public", "restricted", "secret"}


def test_allowed_levels_executive_sees_all():
    assert set(allowed_levels("top_secret")) == {"public", "restricted", "secret", "top_secret"}


def test_allowed_levels_unknown_raises():
    with pytest.raises(KeyError):
        allowed_levels("alien")


def test_clearance_context_is_frozen():
    ctx = ClearanceContext(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        max_clearance="restricted",
        departments=("hr",),
    )
    with pytest.raises(AttributeError):
        ctx.max_clearance = "secret"  # type: ignore[misc]
