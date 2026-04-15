"""Shared test support for organization service unit tests."""

# Standard library
import os
import unittest
from types import SimpleNamespace
from datetime import UTC, datetime
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock

# Third-party
from pyrusult import Ok, Err, ResultStatus


# Test environment bootstrap
os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

# App imports
from gantry.management.organization.services import (
    OrgService,
    OrgNotFoundError,
    InvalidPermissionError,
    OwnerRequiredForGrantError,
    OwnerRemovalNotAllowedError,
    DeletionRequestNotFoundError,
    OwnerPermissionRequiredError,
    OwnerTransferNotAllowedError,
    DeletionAlreadyRequestedError,
    OwnerPermissionImmutableError,
    UserAlreadyInOrganizationError,
    MultipleOrganizationMembershipError,
    UserAlreadyInAnotherOrganizationError,
    ReadOwnPermissionsOrManageRequiredError,
    _extract_org_ids,
)
from gantry.management.organization.permissions import OrgPermission


__all__ = [
    "AsyncMock",
    "BaseOrgServiceTest",
    "DeletionAlreadyRequestedError",
    "DeletionRequestNotFoundError",
    "Err",
    "InvalidPermissionError",
    "Mock",
    "MultipleOrganizationMembershipError",
    "Ok",
    "OrgNotFoundError",
    "OrgPermission",
    "OrgService",
    "OwnerPermissionImmutableError",
    "OwnerPermissionRequiredError",
    "OwnerRemovalNotAllowedError",
    "OwnerRequiredForGrantError",
    "OwnerTransferNotAllowedError",
    "ReadOwnPermissionsOrManageRequiredError",
    "ResultStatus",
    "SimpleNamespace",
    "UTC",
    "UserAlreadyInAnotherOrganizationError",
    "UserAlreadyInOrganizationError",
    "_DummyError",
    "_DummyRedis",
    "_DummySessionManager",
    "_extract_org_ids",
    "datetime",
    "unittest",
]


class _DummySessionManager:
    """Minimal async session manager for service unit tests."""

    def __init__(self):
        self.session = Mock()
        self.session.commit = AsyncMock()
        self.session.flush = AsyncMock()
        self.session.refresh = AsyncMock()

    @asynccontextmanager
    async def get_session(self):
        yield self.session


class _DummyRedis:
    """Minimal Redis stub for organization service unit tests."""

    def __init__(self):
        self.get = AsyncMock(return_value=None)
        self.set = AsyncMock()
        self.delete = AsyncMock()


class _DummyError(Exception):
    """Test-only sentinel error for propagation assertions."""

    pass


class BaseOrgServiceTest(unittest.IsolatedAsyncioTestCase):
    """Base helper for organization service unit tests."""

    def _make_service(self) -> OrgService:
        self.session_manager = _DummySessionManager()
        self.redis = _DummyRedis()
        return OrgService(
            kc_client=Mock(),
            settings_repo=Mock(),
            deletion_repo=Mock(),
            session_manager=self.session_manager,
            logger=Mock(),
            redis=self.redis,
        )
