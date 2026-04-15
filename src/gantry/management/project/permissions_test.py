"""Unit tests for project permission hierarchy and checks."""

import os
import unittest


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.project.permissions import (
    ALL_PERMISSIONS,
    PROJECT_PERMISSIONS_ATTR,
    ProjectPermission,
    has_permission,
    decode_project_permission,
    encode_project_permission,
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
        self.assertTrue(has_permission(perms, ProjectPermission.APIKEY_WRITE))
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

    def test_project_permission_encoding_uses_flat_attr_entries(self):
        """Project permissions should be encoded into one shared attr list."""
        # Act
        attr_name = PROJECT_PERMISSIONS_ATTR
        entry = encode_project_permission("proj-123", "project.owner")
        decoded = decode_project_permission(entry)

        # Assert
        self.assertEqual(attr_name, "project_permissions")
        self.assertEqual(entry, "proj-123:project.owner")
        self.assertEqual(decoded, ("proj-123", "project.owner"))
        self.assertIn(ProjectPermission.OWNER.value, ALL_PERMISSIONS)
        self.assertNotIn("organization.projects.create", ALL_PERMISSIONS)

    def test_decode_project_permission_rejects_invalid_entries(self):
        """Malformed flat entries should be ignored by decoder."""
        # Act + Assert
        self.assertIsNone(decode_project_permission("missing-separator"))
        self.assertIsNone(decode_project_permission(":project.owner"))
        self.assertIsNone(decode_project_permission("proj-1:"))

    def test_invalid_project_permission_strings_do_not_gain_hierarchy(self):
        """Unknown raw permission strings should not grant extra project access."""
        # Arrange
        perms = ["bogus.permission", ProjectPermission.SETTINGS_READ.value]

        # Act + Assert
        self.assertTrue(has_permission(perms, ProjectPermission.SETTINGS_READ))
        self.assertFalse(has_permission(perms, ProjectPermission.USERS_REMOVE))


if __name__ == "__main__":
    unittest.main()
