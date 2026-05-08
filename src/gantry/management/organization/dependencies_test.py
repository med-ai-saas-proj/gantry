import os
import unittest
from types import SimpleNamespace


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.organization.permissions import OrgPermission
from gantry.management.organization.dependencies import (
    getLimit,
    org_settings,
    requiredOrgPermission,
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
    async def test_get_limit_uses_org_override_or_default(self):
        org_service = unittest.mock.Mock()
        org_service.getSettings = unittest.mock.AsyncMock(
            side_effect=[
                unittest.mock.Mock(
                    unwrap=lambda: SimpleNamespace(rate_limit=10)
                ),
                unittest.mock.Mock(
                    unwrap=lambda: SimpleNamespace(rate_limit=None)
                ),
            ]
        )

        self.assertEqual(await getLimit("org-1", org_service), 10)
        self.assertEqual(
            await getLimit("org-1", org_service),
            org_settings.default_rate_limit,
        )

    def test_permission_helpers(self):
        member_missing = _raise_permission_fetch_error(_MemberMissingErr())
        self.assertIsInstance(member_missing, _InsufficientOrgPermission)

        upstream_err = _raise_permission_fetch_error(ValueError("plain"))
        self.assertEqual(getattr(upstream_err, "status", None), 502)

        wrapped_err = _raise_permission_fetch_error(_DummyErr())
        self.assertEqual(getattr(wrapped_err, "status", None), 502)

        passthrough_err = _raise_permission_fetch_error(_UpstreamClientErr())
        self.assertIsInstance(passthrough_err, _UpstreamClientErr)

    async def test_required_org_permission_uses_user_info_permissions(self):
        dependency = requiredOrgPermission(OrgPermission.SETTINGS_READ)
        allowed_user = {
            "id": "u1",
            "username": "alice",
            "email": "a@test",
            "org_uuid": "org-1",
            "org_permissions": ["organization.settings.read"],
            "project_permissions": {},
        }
        denied_user = {
            "id": "u1",
            "username": "alice",
            "email": "a@test",
            "org_uuid": "org-1",
            "org_permissions": [],
            "project_permissions": {},
        }

        self.assertEqual(await dependency(allowed_user), allowed_user)
        with self.assertRaises(_InsufficientOrgPermission):
            await dependency(denied_user)
