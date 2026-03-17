"""Compatibility shim that re-exports split project service tests."""

from .services_core_test import TestProjectServiceCore
from .services_state_test import TestProjectServiceState
from .services_membership_test import TestProjectServiceMembership
from .services_permission_updates_test import (
    TestProjectServicePermissionUpdates,
)


__all__ = [
    "TestProjectServiceCore",
    "TestProjectServiceMembership",
    "TestProjectServicePermissionUpdates",
    "TestProjectServiceState",
]
