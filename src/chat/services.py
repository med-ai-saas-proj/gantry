"""This file contain definition of chat's services."""

from src.db.postgres.service import PostgresService

from . import repositories

from typing import Callable
from contextlib import _GeneratorContextManager

from structlog.stdlib import BoundLogger


class ExampleServices:
    def __init__(
        self,
        session_scope: Callable[..., _GeneratorContextManager],
        logger: BoundLogger,
    ):
        self.postgres_service = PostgresService(session_scope)

    async def example_insert(self):
        record = await self.postgres_service.insert(
            repo=repositories.ExampleRepo,
            record={"field": "slkdf"},
            returning=True,
        )
