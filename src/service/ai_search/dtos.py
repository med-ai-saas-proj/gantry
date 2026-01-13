from ..utils.agent.dtos.generation_input import GenerationInput

from typing import Optional, Annotated, TypedDict

from pydantic import Field


class AiSearchInput(GenerationInput):
    """AI search input."""

    query: Annotated[str, Field(description="Search query")]
