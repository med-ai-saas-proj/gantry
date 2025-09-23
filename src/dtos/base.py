from typing import Generic, TypeVar
from pydantic import (
    BaseModel,
    ConfigDict,
    TypeAdapter,
    Field,
    field_validator,
    model_validator,
    ValidationError,
)


PYDANTIC_DISCRIMINATOR_KEY = "[__BACKEND_PYDANTIC_DICRIMINATOR__]."

T = TypeVar("T")


class GenerateTypeAdapter(Generic[T]):
    def __new__(cls, type):
        dto = TypeAdapter[T](type=type)
        return dto


class BaseDTO(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True, plugin_settings={"observe": "all"}
    )
