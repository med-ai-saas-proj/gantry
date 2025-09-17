from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, TypeAdapter


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
