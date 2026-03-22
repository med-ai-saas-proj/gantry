import os
from typing import TypedDict

import pydantic_ai


pydantic_ai.Agent()
from pydantic import create_model
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from sqlalchemy.util.typing import NotRequired


class Test2(BaseSettings):
    foo: int
    bar: str
    stuff_sdf: int


class Test(BaseSettings):
    baz: bool


class PydanticField[T: BaseSettings](TypedDict):
    prefix: str
    setting: type[T]
    default: NotRequired[T]


type_arr: list[PydanticField] = []


def register[T](t: PydanticField[T]):
    type_arr.append(t)


def initCentralSetting() -> type[BaseSettings]:
    CentralSetting = create_model(
        "CentralSetting",
        __base__=BaseSettings,
        __config__=SettingsConfigDict(
            cli_parse_args=True,
            case_sensitive=False,
            env_nested_delimiter="_",
            env_nested_max_split=1,
        ),
        **{
            fieldd["prefix"]: (
                fieldd["setting"],
                fieldd["default"] if "default" in fieldd else ...,
            )
            for fieldd in type_arr
        },
    )

    return CentralSetting


from fastuuid import uuid7, uuid7_bulk


if __name__ == "__main__":
    os.environ["TEST2_FOO"] = "1"
    os.environ["TEST2_BAR"] = "asldfk"
    os.environ["TEST2_STUFF_SDF"] = "10"
    os.environ["TEST_BAZ"] = "False"

    register({"prefix": "test", "setting": Test})
    register({"prefix": "test2", "setting": Test2})
    # print(Test())
    # print(initCentralSetting()())
    # print(TestSubmodule())

    prev = uuid7().bytes
    for i in range(100):
        now = uuid7().bytes
        assert now > prev
        prev = now

    ls = uuid7_bulk(100)
    print(ls)
    for prev, next in zip(ls[:-1], ls[1:], strict=True):
        assert prev.bytes < next.bytes
