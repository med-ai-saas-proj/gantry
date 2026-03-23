import os
import sys
from typing import Callable, ClassVar, final
from functools import lru_cache

from pydantic import create_model
from pydantic_settings import (
    CliApp,
    BaseSettings,
    SettingsConfigDict,
)


# class AppSettings(BaseSettings):
#     model_config = SettingsConfigDict(
#         cli_parse_args=True,
#         case_sensitive=False,
#         env_nested_delimiter="_",
#         env_nested_max_split=1,
#     )
#     port: int = 9000
#     pass


# @final
# class CentralizedSettings:
#     """Register your settings here, used to build CLI."""

#     type_arr: ClassVar[dict[str, type[BaseSettings]]] = {}

#     @classmethod
#     def register[T: type[BaseSettings]](cls, prefix: str) -> Callable[[T], T]:
#         """Decorator to register your settings, pls use an appropriate prefix."""

#         def wrapper(setting: T) -> T:
#             setting.model_config.update(
#                 env_prefix=f"{prefix}_",
#                 cli_parse_args=True,
#                 cli_prefix=prefix,
#                 cli_ignore_unknown_args=True,
#             )
#             cls.type_arr[prefix] = setting
#             return setting

#         return wrapper

#     @classmethod
#     @lru_cache(1)
#     def getCentralSettingType(cls) -> type[AppSettings]:
#         Model = create_model(
#             "TMP",
#             __base__=AppSettings,
#             **cls.type_arr,
#         )
#         return Model

#     @classmethod
#     @lru_cache(1)
#     def getCentralSetting(cls) -> BaseSettings:
#         return cls.getCentralSettingType()()


# @CentralizedSettings.register("test2")
# class Test2(BaseSettings):
#     foo: int
#     bar: str
#     stuff_sdf: int


# @CentralizedSettings.register("test")
# class Test(BaseSettings):
#     baz: bool


# @lru_cache(1)
# def getTestSettings():
#     return Test()


# @lru_cache(1)
# def getTest2Settings():
#     return Test2()


if __name__ == "__main__":
    os.environ["TEST2_FOO"] = "1"
    os.environ["TEST2_BAR"] = "asldfk"
    os.environ["TEST2_STUFF_SDF"] = "10"
    os.environ["TEST_BAZ"] = "False"
    CliApp.print_help(CentralizedSettings.getCentralSettingType())
    sys.argv = ["shit ass", "--test.baz=True"]

    print(CentralizedSettings.getCentralSetting())
    print(getTestSettings())
    print(getTest2Settings())
