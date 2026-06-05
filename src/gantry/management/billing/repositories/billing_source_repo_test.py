from ..models import BillingSourceProvider
from .billing_source_repo import BillingSourceRepo

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


class BillingSourceRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_for_org_returns_scalar_without_db(self):
        source = SimpleNamespace(organization_id="org1")
        result = MagicMock()
        result.scalar_one_or_none.return_value = source
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = BillingSourceRepo()

        found = await repo.getForOrg(session, "org1")

        assert found is source
        session.execute.assert_awaited_once()

    async def test_get_with_lock_uses_for_update_read_branch(self):
        source = SimpleNamespace(organization_id="org1")
        result = MagicMock()
        result.scalar_one_or_none.return_value = source
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = BillingSourceRepo()

        found = await repo.getWithLock(
            session,
            org_id="org1",
            provider=BillingSourceProvider.STRIPE,
            read=True,
        )

        stmt = session.execute.call_args.args[0]
        assert getattr(stmt, "_for_update_arg").read is True
        assert found is source

    async def test_get_with_lock_uses_write_lock_by_default(self):
        source = SimpleNamespace(organization_id="org1")
        result = MagicMock()
        result.scalar_one_or_none.return_value = source
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = BillingSourceRepo()

        found = await repo.getWithLock(
            session,
            org_id="org1",
            provider=BillingSourceProvider.STRIPE,
        )

        stmt = session.execute.call_args.args[0]
        assert getattr(stmt, "_for_update_arg").read is False
        assert found is source
