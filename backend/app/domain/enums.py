from __future__ import annotations

from enum import Enum
from functools import total_ordering


@total_ordering
class ClearanceLevel(str, Enum):
    PUBLIC = "public"
    RESTRICTED = "restricted"
    SECRET = "secret"
    TOP_SECRET = "top_secret"

    @property
    def _rank(self) -> int:
        return {"public": 0, "restricted": 1, "secret": 2, "top_secret": 3}[self.value]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ClearanceLevel):
            return NotImplemented
        return self._rank < other._rank


class Role(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    DIRECTOR = "director"
    EXECUTIVE = "executive"

    def max_clearance(self) -> ClearanceLevel:
        return {
            Role.EMPLOYEE: ClearanceLevel.PUBLIC,
            Role.MANAGER: ClearanceLevel.RESTRICTED,
            Role.DIRECTOR: ClearanceLevel.SECRET,
            Role.EXECUTIVE: ClearanceLevel.TOP_SECRET,
        }[self]

    def can_see(self, classification: ClearanceLevel) -> bool:
        return classification <= self.max_clearance()


class Department(str, Enum):
    HR = "hr"
    SECURITY = "security"
    ENGINEERING = "engineering"
    FLEET_OPERATIONS = "fleet_operations"
    PROCUREMENT = "procurement"
    IT = "it"
