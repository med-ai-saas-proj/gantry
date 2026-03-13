"""Unit tests for project permission hierarchy and checks."""

import os
import unittest


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.project.permissions import (
    ProjectPermission,
    has_permission,
    get_effective_permissions,
)


class TestProjectPermissions(unittest.TestCase):
    """Validate project permission inheritance behavior."""

    def test_owner_inherits_only_project_scoped_permissions(self):
        """Project owner inherits only project-local permissions."""
        # Arrange
        perms = [ProjectPermission.OWNER.value]

        # Act
        effective = get_effective_permissions(perms)

        # Assert
        self.assertIn(ProjectPermission.USERS_ADD.value, effective)
        self.assertTrue(
            has_permission(perms, ProjectPermission.USERS_PERMISSIONS_RW)
        )
        self.assertFalse(
            has_permission(perms, ProjectPermission.PROJECTS_CREATE)
        )
        self.assertFalse(
            has_permission(perms, ProjectPermission.PROJECTS_GET_ALL)
        )

    def test_non_owner_does_not_inherit(self):
        """Non-owner should not automatically inherit write permission."""
        # Arrange
        perms = [ProjectPermission.SETTINGS_READ.value]

        # Act + Assert
        self.assertFalse(
            has_permission(perms, ProjectPermission.SETTINGS_WRITE)
        )


if __name__ == "__main__":
    unittest.main()
