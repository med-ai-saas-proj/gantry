from gantry.db import AsyncSessionManager
from gantry.shared.utils.scaled_amount import scaled_amount_to_decimal

from ..dtos import ScaledAmount, CreditTransactionInfoResponse
from ..repositories.credit_repo import CreditRepo

from decimal import Decimal


class CreditService:
    def __init__(
        self,
        session_manager: AsyncSessionManager,
        credit_repository: CreditRepo,
    ):
        self.credit_repository = credit_repository
        self.session_manager = session_manager

    async def getAvailableCredits(self, org_id: str) -> Decimal:
        async with self.session_manager.get_session() as session:
            credit = await self.credit_repository.getCreditByOrgId(
                session, org_id
            )
        return credit.amount if credit else Decimal(0)

    async def addCredits(
        self,
        org_id: str,
        amount_to_add: ScaledAmount,
        description: str | None = None,
    ) -> Decimal:
        amount = scaled_amount_to_decimal(amount_to_add)
        if amount <= 0:
            raise ValueError("Amount to add must be greater than 0.")
        description = description or "Added credits"

        async with self.session_manager.get_session() as session:
            async with session.begin():
                res = await self.credit_repository.addCreditForOrg(
                    session, org_id, amount
                )
                await self.credit_repository.createCreditTransaction(
                    session, org_id, amount, description
                )
                await session.commit()
                return res.amount

    async def getCreditTransactions(
        self,
        org_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[CreditTransactionInfoResponse], int]:
        async with self.session_manager.get_session() as session:
            (
                transactions,
                total,
            ) = await self.credit_repository.getCreditTransactions(
                session, org_id, offset, limit
            )
            return (
                [
                    CreditTransactionInfoResponse(
                        amount=tx["amount"],
                        description=tx["description"],
                        created_at=tx["created_at"],
                    )
                    for tx in transactions
                ],
                total,
            )
