"""
Role-Based Access Control.

Three roles are enough for most enterprise deployments of this backend;
add more here as needed. Roles are ordered from least to most privileged,
which `require_role` uses to allow higher roles to satisfy a lower-role
requirement.
"""
from enum import Enum


class Role(str, Enum):
    VIEWER = "viewer"      # can chat and read reports
    ANALYST = "analyst"    # can also trigger schema refresh / health analysis
    ADMIN = "admin"        # full access incl. user management, alert config

    @property
    def rank(self) -> int:
        return [Role.VIEWER, Role.ANALYST, Role.ADMIN].index(self)


def role_satisfies(user_role: str, required_role: Role) -> bool:
    try:
        return Role(user_role).rank >= required_role.rank
    except ValueError:
        return False
