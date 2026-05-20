from ..models import BillingSourceProvider
from .billing_source_service import BillingSourceService
from ..repositories.billing_source_repo import BillingSourceRepo

import unittest
from uuid import UUID
from types import SimpleNamespace
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from pyrusult import Ok, ResultStatus


class _AsyncContextManager:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionManager:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        return _AsyncContextManager(self.session)


class BillingSourceServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_billing_source_or_error_returns_err_when_missing(self):
        session = MagicMock()
        repo = MagicMock(spec=BillingSourceRepo)
        repo.getForOrg = AsyncMock(return_value=None)
        service = BillingSourceService(
            billing_source_repo=repo,
            session_manager=_SessionManager(session),
            redis_client=MagicMock(),
            stripe_client=MagicMock(),
        )

        res = await service._getBillingSourceOrError("org1")

        assert res.status == ResultStatus.Err

    async def test_create_setup_intent_delegates_to_provider(self):
        session = MagicMock()
        repo = MagicMock(spec=BillingSourceRepo)
        repo.getForOrg = AsyncMock(
            return_value=SimpleNamespace(
                uuid=UUID("123e4567-e89b-12d3-a456-426614174000"),
                organization_id="org1",
                source_type=BillingSourceProvider.STRIPE,
                created_at=datetime(2026, 1, 15),
                provider_id="cus_123",
            )
        )
        service = BillingSourceService(
            billing_source_repo=repo,
            session_manager=_SessionManager(session),
            redis_client=MagicMock(),
            stripe_client=MagicMock(),
        )
        provider = MagicMock()
        provider.createSetupIntent = AsyncMock(
            return_value=Ok({"client_secret": "secret"})
        )
        service.provider_impl = {BillingSourceProvider.STRIPE: provider}

        res = await service.createSetupIntent("org1")

        assert res.status == ResultStatus.Ok
        provider.createSetupIntent.assert_awaited_once_with("cus_123")

    async def test_get_billing_source_maps_provider_customer(self):
        session = MagicMock()
        repo = MagicMock(spec=BillingSourceRepo)
        repo.getForOrg = AsyncMock(
            return_value=SimpleNamespace(
                uuid=UUID("123e4567-e89b-12d3-a456-426614174000"),
                organization_id="org1",
                source_type=BillingSourceProvider.STRIPE,
                created_at=datetime(2026, 1, 15),
                provider_id="cus_123",
            )
        )
        service = BillingSourceService(
            billing_source_repo=repo,
            session_manager=_SessionManager(session),
            redis_client=MagicMock(),
            stripe_client=MagicMock(),
        )
        provider = MagicMock()
        provider.getCustomer = AsyncMock(
            return_value=Ok(
                SimpleNamespace(
                    email="user@example.com",
                    phone="123",
                    name="Test User",
                    address=SimpleNamespace(
                        line1="1 Main St",
                        line2=None,
                        city="City",
                        state="CA",
                        postal_code="12345",
                        country="US",
                    ),
                )
            )
        )
        service.provider_impl = {BillingSourceProvider.STRIPE: provider}

        res = await service.getBillingSource("org1")

        assert res.status == ResultStatus.Ok
        assert res.unwrap().email == "user@example.com"
