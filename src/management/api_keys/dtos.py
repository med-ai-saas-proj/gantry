from src.shared.dtos.base import BaseDTO

from typing import TypedDict


class CreateAPIKeyInput(BaseDTO):
    """Input DTO for creating an API key."""

    name: str | None
    project_id: str
    permissions: list[str]


class CreateAPIKeyOutputSuccess(TypedDict):
    """Output DTO for successful API key creation."""

    key: str
