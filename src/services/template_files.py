from typing import Callable
from contextlib import _GeneratorContextManager

from src.services import PostgresService


class TemplateFileService:

    def __init__(self, session_scope: Callable[..., _GeneratorContextManager]):
        self.postgres_service = PostgresService(session_scope=session_scope)
        self.session_scope = session_scope
