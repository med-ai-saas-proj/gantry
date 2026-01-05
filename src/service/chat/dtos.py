"""This file contain definition of chat's data transfer objects."""

from ..utils.agent.dtos.model import ModelInput
from ..utils.agent.dtos.generation_input import GenerationInput

from typing import Annotated

from pydantic import Field


class ChatInput(GenerationInput):
    """Chat input."""

    input: Annotated[ModelInput, Field(description="Model's input")]
