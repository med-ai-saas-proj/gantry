import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

from safe_result import Ok, Err


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.organization.permissions import OrgPermission
from src.management.organization.dependencies import (
    getLimit,
    org_settings,
    _get_user_info,
    requiredOrgPermission,
    _get_permissions_or_raise,
    _InsufficientOrgPermission,
    _raise_permission_fetch_error,
)


class _DummyErr(Exception):
    status = 500
    code = "boom"
    detail = "failed"


class _MemberMissingErr(Exception):
    status = 404
    code = "member_not_found"


class _UpstreamClientErr(Exception):
    status = 400
    code = "bad_request"


class TestOrganizationDependencies(unittest.IsolatedAsyncioTestCase):
    async def test_get_user_info_and_limit(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {"id": "u1", "roles": [], "org_id": "org-1"}
        )
        self.assertEqual(
            await _get_user_info("token", auth_service),
            {"id": "u1", "roles": [], "org_id": "org-1"},
        )

        org_service = Mock()
        org_service.get_settings = AsyncMock(
            side_effect=[
                Ok(SimpleNamespace(rate_limit=10)),
                Ok(SimpleNamespace(rate_limit=None)),
            ]
        )
        self.assertEqual(await getLimit("org-1", org_service), 10)
        self.assertEqual(
            await getLimit("org-1", org_service),
            org_settings.default_rate_limit,
        )

    def test_permission_helpers(self):
        with self.assertRaises(_InsufficientOrgPermission):
            _raise_permission_fetch_error(_MemberMissingErr())

        with self.assertRaises(Exception) as upstream_ctx:
            _raise_permission_fetch_error(ValueError("plain"))
        self.assertEqual(getattr(upstream_ctx.exception, "status", None), 502)

        with self.assertRaises(Exception) as wrapped_ctx:
            _raise_permission_fetch_error(_DummyErr())
        self.assertEqual(getattr(wrapped_ctx.exception, "status", None), 502)

        with self.assertRaises(_UpstreamClientErr):
            _raise_permission_fetch_error(_UpstreamClientErr())

    async def test_get_permissions_or_raise_and_required_permission(self):
        org_service = Mock()
        org_service.get_user_permissions = AsyncMock(
            side_effect=[
                Ok(SimpleNamespace(permissions=["organization.settings.read"])),
                Err(_MemberMissingErr()),
                Ok(SimpleNamespace(permissions=["organization.owner"])),
            ]
        )

        self.assertEqual(
            await _get_permissions_or_raise(org_service, "org-1", "u1"),
            ["organization.settings.read"],
        )
        with self.assertRaises(_InsufficientOrgPermission):
            await _get_permissions_or_raise(org_service, "org-1", "u1")

        dependency = requiredOrgPermission(OrgPermission.SETTINGS_READ)
        user_info = {"id": "u1", "roles": []}
        self.assertEqual(
            await dependency("org-1", user_info, org_service), user_info
        )

    async def test_required_org_permission_deny(self):
        dependency = requiredOrgPermission(OrgPermission.SETTINGS_READ)
        org_service = Mock()
        org_service.get_user_permissions = AsyncMock(
            return_value=Ok(SimpleNamespace(permissions=[]))
        )
        with self.assertRaises(_InsufficientOrgPermission):
            await dependency("org-1", {"id": "u1", "roles": []}, org_service)
