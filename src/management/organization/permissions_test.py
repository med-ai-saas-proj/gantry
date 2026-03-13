"""Unit tests for organization permission hierarchy and checks."""

import os
import unittest


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.organization.permissions import (
    OrgPermission,
    has_permission,
    get_effective_permissions,
)


class TestOrgPermissions(unittest.TestCase):
    """Validate organization permission inheritance behavior."""

    def test_owner_inherits_all(self):
        """Owner should implicitly have all child org permissions."""
        # Arrange
        perms = [OrgPermission.OWNER.value]

        # Act
        effective = get_effective_permissions(perms)

        # Assert
        self.assertIn(OrgPermission.USERS_GET_ALL.value, effective)
        self.assertIn(OrgPermission.SETTINGS_WRITE.value, effective)
        self.assertTrue(has_permission(perms, OrgPermission.INVITE))

    def test_missing_permission_returns_false(self):
        """A non-owner without explicit permission should be denied."""
        # Arrange
        perms = [OrgPermission.SETTINGS_READ.value]

        # Act + Assert
        self.assertFalse(has_permission(perms, OrgPermission.USERS_REMOVE))


if __name__ == "__main__":
    unittest.main()
