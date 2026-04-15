"""Shared test support for project service unit tests."""

# Standard library
import os
import unittest
from types import SimpleNamespace
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock

# Third-party
from pyrusult import Ok, Err, ResultStatus


# Test environment bootstrap
os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

# App imports
from gantry.management.project.services import (
    ProjectService,
    ProjectArchivedError,
    ProjectNotFoundError,
    UserNotInProjectError,
    UserAlreadyInProjectError,
    OwnerRequiredForGrantError,
    InvalidProjectPermissionError,
    LastOwnerRemovalNotAllowedError,
    InsufficientProjectPermissionError,
)
from gantry.management.project.permissions import (
    PROJECT_PERMISSIONS_ATTR,
    ProjectPermission,
    encode_project_permission,
)


__all__ = [
    "AsyncMock",
    "BaseProjectServiceTest",
    "Err",
    "InsufficientProjectPermissionError",
    "InvalidProjectPermissionError",
    "LastOwnerRemovalNotAllowedError",
    "Mock",
    "Ok",
    "PROJECT_PERMISSIONS_ATTR",
    "ProjectArchivedError",
    "ProjectNotFoundError",
    "ProjectPermission",
    "ProjectService",
    "ResultStatus",
    "SimpleNamespace",
    "UserAlreadyInProjectError",
    "UserNotInProjectError",
    "_DummyError",
    "_DummyRedis",
    "_DummySessionManager",
    "encode_project_permission",
    "OwnerRequiredForGrantError",
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
    """Minimal Redis stub for project service unit tests."""

    def __init__(self):
        self.get = AsyncMock(return_value=None)
        self.set = AsyncMock()
        self.delete = AsyncMock()


class _DummyError(Exception):
    """Test-only sentinel error for propagation assertions."""

    pass


class BaseProjectServiceTest(unittest.IsolatedAsyncioTestCase):
    """Base helper for project service unit tests."""

    def _make_service(self) -> ProjectService:
        self.session_manager = _DummySessionManager()
        self.redis = _DummyRedis()
        service = ProjectService(
            session_manager=self.session_manager,
            logger=Mock(),
            project_repo=Mock(),
            membership_repo=Mock(),
            settings_repo=Mock(),
            kc_client=Mock(),
            redis=self.redis,
        )
        service._isOrgOwner = AsyncMock(return_value=Ok(False))
        return service
