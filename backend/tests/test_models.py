import uuid

from app.domain.enums import Role
from app.domain.models import Tenant, User


def test_tenant_has_expected_columns():
    t = Tenant(name="Galactic Empire", role_label_map={"employee": "Imperial Employee"})
    assert t.name == "Galactic Empire"
    assert t.role_label_map["employee"] == "Imperial Employee"


def test_user_default_departments_is_empty_list():
    u = User(
        tenant_id=uuid.uuid4(),
        username="ts-001",
        password_hash="x",
        role=Role.EMPLOYEE.value,
        max_clearance="public",
    )
    assert u.departments == []
