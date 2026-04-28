import os
import ast
import unittest
from pathlib import Path


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.api_keys.permissions import (
    listPermissions,
    clearPermissions,
    registerPermissions,
    doneRegisterPermission,
    hasOnlyRegisteredPermissions,
    isPermissionRegistrationDone,
)


class _RequiredPermissionsCollector(ast.NodeVisitor):
    def __init__(self):
        self.permissions: set[str] = set()

    def visit_Call(self, node: ast.Call):
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "requiredPermissions"
            and node.args
            and isinstance(node.args[0], ast.List)
        ):
            for elt in node.args[0].elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.permissions.add(elt.value)
        self.generic_visit(node)


class TestApiKeyPermissionsRegistry(unittest.TestCase):
    def setUp(self):
        clearPermissions()

    def test_registry_tracks_dynamic_permissions(self):
        registerPermissions(["chat.read", "file.read", "chat.read"])

        self.assertEqual(listPermissions(), ["chat.read", "file.read"])

    def test_registry_validates_only_registered_permissions(self):
        registerPermissions(["chat.read"])

        self.assertTrue(hasOnlyRegisteredPermissions(["chat.read"]))
        self.assertFalse(hasOnlyRegisteredPermissions(["unknown.permission"]))

    def test_done_register_permission_finalizes_registry(self):
        registerPermissions(["chat.read"])

        doneRegisterPermission()

        self.assertTrue(isPermissionRegistrationDone())
        registerPermissions(["chat.read"])
        with self.assertRaises(RuntimeError):
            registerPermissions(["file.read"])

    def test_service_routes_declare_expected_dynamic_permissions(self):
        collector = _RequiredPermissionsCollector()
        for path in [
            Path("src/gantry/service/utils/conversation/routers.py"),
            Path("src/gantry/service/utils/file_storage/routers/api.py"),
        ]:
            collector.visit(ast.parse(path.read_text(), filename=str(path)))

        self.assertEqual(
            sorted(collector.permissions),
            [
                "conversation.delete",
                "conversation.read",
                "conversation.write",
                "file.delete",
                "file.read",
                "file.write",
            ],
        )
