"""Compatibility shim that re-exports split organization service tests."""

from .services_lifecycle_test import TestOrgServiceLifecycle
from .services_invitations_test import TestOrgServiceInvitations
from .services_permissions_test import TestOrgServicePermissions


__all__ = [
    "TestOrgServiceInvitations",
    "TestOrgServiceLifecycle",
    "TestOrgServicePermissions",
]
