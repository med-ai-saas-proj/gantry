from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    TomlConfigSettingsSource,
    PydanticBaseSettingsSource,
)


class TomlPathConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(
        self,
        settings_cls: type[BaseSettings],
        in_path: str,
        out_path: str | None = None,
    ):
        self.in_path = in_path
        self.out_path = out_path
        super().__init__(settings_cls)

    def __call__(self) -> dict[str, Any]:
        in_path = self.current_state
        try:
            items = self.in_path.split(".")
            for item in items:
                in_path = in_path.get(item)
        except:
            in_path = None
        if in_path is not None:
            res = TomlConfigSettingsSource(self.settings_cls, in_path)()
            if self.out_path is None:
                return res
            else:
                final_res = {}
                tmp = final_res
                items = self.out_path.split(".")
                for item in items[:-1]:
                    tmp[item] = {}
                    tmp = tmp[item]
                tmp[items[-1]] = res
                return final_res
        return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False


class DotEnvPathConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(
        self,
        settings_cls: type[BaseSettings],
        in_path: str,
        out_path: str | None = None,
    ):
        self.in_path = in_path
        self.out_path = out_path
        super().__init__(settings_cls)

    def __call__(self) -> dict[str, Any]:
        in_path = self.current_state
        try:
            items = self.in_path.split(".")
            for item in items:
                in_path = in_path.get(item)
        except:
            in_path = None
        if in_path is not None:
            res = DotEnvSettingsSource(self.settings_cls, in_path)()
            if self.out_path is None:
                return res
            else:
                final_res = {}
                tmp = final_res
                items = self.out_path.split(".")
                for item in items[:-1]:
                    tmp[item] = {}
                    tmp = tmp[item]
                tmp[items[-1]] = res
                return final_res
        return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False
