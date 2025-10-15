from src.shared.dtos.generation_input import GenerationInput
from src.shared.dtos.generation_output import (
    Citation,
    GenerationOutput,
)

from typing import Optional, Annotated, TypedDict

from pydantic import Field
from sqlalchemy.testing.util import total_size


class AiSearchInput(GenerationInput):
    """AI search input."""

    query: Annotated[str, Field(description="Search query")]


class Answer(TypedDict):
    """AI generated answer."""

    result: Annotated[str, Field(description="The search query's answer")]
    reasoning: Annotated[
        Optional[str],
        Field(description="Model's reasoning, only available for some model"),
    ]
    citations: Annotated[
        list[Citation], Field(description="Model response's citation.")
    ]
    viewed_pages: Annotated[
        list[str],
        Field(description="A list of urls, that the model have looked though."),
    ]


AiSearchOutput = GenerationOutput[Answer]
