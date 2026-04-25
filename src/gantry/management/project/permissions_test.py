"""Unit tests for project permission hierarchy and checks."""

import os
import unittest


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.shared.project_permissions import (
    normalize_project_permission_map,
    serialize_project_permission_map,
    serialize_project_permission_values,
)
from gantry.management.project.permissions import (
    ALL_PERMISSIONS,
    PROJECT_PERMISSIONS_ATTR,
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

    def test_project_permission_helpers_support_grouped_attr_map(self):
        """Project permissions should persist as one grouped attr object."""
        # Act
        attr_name = PROJECT_PERMISSIONS_ATTR
        encoded = serialize_project_permission_map(
            {
                "proj-123": [
                    "project.owner",
                    "project.settings.read",
                    "project.owner",
                ]
            }
        )

        # Assert
        self.assertEqual(attr_name, "project_permissions")
        self.assertEqual(
            encoded,
            {
                "proj-123": [
                    "project.owner",
                    "project.settings.read",
                ]
            },
        )
        self.assertIn(ProjectPermission.OWNER.value, ALL_PERMISSIONS)
        self.assertNotIn("organization.projects.create", ALL_PERMISSIONS)

    def test_normalize_project_permission_map_ignores_old_flat_entries(self):
        """Only the grouped map format should be accepted."""
        # Act + Assert
        self.assertEqual(
            normalize_project_permission_map(
                [
                    "proj-1:project.owner",
                    "proj-1:project.settings.read",
                    "proj-2:apikey.read",
                ]
            ),
            {},
        )

    def test_keycloak_values_store_one_json_object_per_project(self):
        """Raw Keycloak values should split grouped permissions per project."""
        self.assertEqual(
            serialize_project_permission_values(
                {
                    "proj-1": ["project.owner", "project.owner"],
                    "proj-2": ["apikey.read"],
                }
            ),
            [
                '{"proj-1":["project.owner"]}',
                '{"proj-2":["apikey.read"]}',
            ],
        )

    def test_invalid_project_permission_strings_do_not_gain_hierarchy(self):
        """Unknown raw permission strings should not grant extra project access."""
        # Arrange
        perms = ["bogus.permission", ProjectPermission.SETTINGS_READ.value]

        # Act + Assert
        self.assertTrue(has_permission(perms, ProjectPermission.SETTINGS_READ))
        self.assertFalse(has_permission(perms, ProjectPermission.USERS_REMOVE))


if __name__ == "__main__":
    unittest.main()
