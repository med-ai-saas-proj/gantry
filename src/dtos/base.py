from typing import Generic, TypeVar
from typing_extensions import TypedDict
from pydantic import ConfigDict, TypeAdapter, with_config


PYDANTIC_DISCRIMINATOR_KEY = "[__BACKEND_PYDANTIC_DICRIMINATOR__]."

T = TypeVar("T")


class GenerateTypeAdapter(Generic[T]):
    def __new__(cls, type):
        dto = TypeAdapter[T](type=type)
        return dto


@with_config(
    ConfigDict(use_enum_values=True, plugin_settings={"observe": "all"})
)
class BaseDTO(TypedDict):
    pass
