"""Unit tests for project DTO validation."""

import os
import unittest

from pydantic import ValidationError


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.project.dtos import CreateProjectRequest


class TestProjectDTOs(unittest.TestCase):
    """Validate request DTOs for project APIs."""

    def test_create_project_request_valid(self):
        """DTO should accept valid name and optional description."""
        # Arrange + Act
        dto = CreateProjectRequest(name="Alpha", description="demo")

        # Assert
        self.assertEqual(dto.name, "Alpha")
        self.assertEqual(dto.description, "demo")

    def test_create_project_request_name_required(self):
        """DTO should reject empty project name."""
        # Act + Assert
        with self.assertRaises(ValidationError):
            CreateProjectRequest(name="", description=None)


if __name__ == "__main__":
    unittest.main()
