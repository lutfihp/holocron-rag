import pytest

from app.domain.enums import ClearanceLevel, Department, Role


def test_clearance_level_ordering():
    assert ClearanceLevel.PUBLIC < ClearanceLevel.RESTRICTED
    assert ClearanceLevel.RESTRICTED < ClearanceLevel.SECRET
    assert ClearanceLevel.SECRET < ClearanceLevel.TOP_SECRET


def test_clearance_level_values_are_db_strings():
    assert ClearanceLevel.PUBLIC.value == "public"
    assert ClearanceLevel.TOP_SECRET.value == "top_secret"


@pytest.mark.parametrize(
    "role,expected_max",
    [
        (Role.EMPLOYEE, ClearanceLevel.PUBLIC),
        (Role.MANAGER, ClearanceLevel.RESTRICTED),
        (Role.DIRECTOR, ClearanceLevel.SECRET),
        (Role.EXECUTIVE, ClearanceLevel.TOP_SECRET),
    ],
)
def test_role_max_clearance_mapping(role, expected_max):
    assert role.max_clearance() == expected_max


def test_role_can_see_uses_max_clearance():
    assert Role.MANAGER.can_see(ClearanceLevel.PUBLIC) is True
    assert Role.MANAGER.can_see(ClearanceLevel.RESTRICTED) is True
    assert Role.MANAGER.can_see(ClearanceLevel.SECRET) is False


def test_departments_listed():
    expected = {"hr", "security", "engineering", "fleet_operations", "procurement", "it"}
    assert {d.value for d in Department} == expected
