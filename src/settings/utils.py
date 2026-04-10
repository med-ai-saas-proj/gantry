from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    TomlConfigSettingsSource,
    PydanticBaseSettingsSource,
)


class TomlPathConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], path: str):
        self.path = path
        super().__init__(settings_cls)

    def __call__(self) -> dict[str, Any]:
        path = self.current_state
        try:
            items = self.path.split(".")
            for item in items:
                path = path.get(item)
        except:
            path = None
        if path is not None:
            tmp = TomlConfigSettingsSource(self.settings_cls, path)()
            return {"server": tmp}
        return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False


class DotEnvPathConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], path: str):
        self.path = path
        super().__init__(settings_cls)

    def __call__(self) -> dict[str, Any]:
        path = self.current_state
        try:
            items = self.path.split(".")
            for item in items:
                path = path.get(item)
        except:
            path = None
        if path is not None:
            tmp = DotEnvSettingsSource(self.settings_cls, path)()
            return {"server": tmp}
        return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False
