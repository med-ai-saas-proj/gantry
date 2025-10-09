from src.shared.dtos.generation_input import GenerationInput
from src.shared.dtos.generation_output import (
    GenerationOutput,
    ReferenceCitationMixin,
)

from typing import Any, Union, Optional, Annotated, TypedDict, NotRequired

from pydantic import Field


class AiSearchInput(GenerationInput):
    """AI search input."""

    query: Annotated[str, Field(description="Search query")]


class Answer(ReferenceCitationMixin):
    """AI generated answer."""

    result: Annotated[str, Field(description="The search query's answer")]
    reasoning: Annotated[
        Optional[str],
        Field(description="Model's reasoning, only available for some model"),
    ]


AiSearchOutput = GenerationOutput[Answer]
