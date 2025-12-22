from src.shared.dtos.base import BaseDTO

from typing import TypedDict

from pydantic import Field


class CreateAPIKeyInput(BaseDTO):
    """Input DTO for creating an API key."""

    name: str = Field("Api Key")
    description: str = Field("")
    project_id: str
    permissions: list[str]


class CreateAPIKeyOutputSuccess(TypedDict):
    """Output DTO for successful API key creation."""

    key: str
    hint: str
