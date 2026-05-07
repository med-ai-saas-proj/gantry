from typing import TypedDict


class UserInfo(TypedDict):
    id: str
    username: str | None
    email: str | None
    org_uuid: str
    org_permissions: list[str]
    project_permissions: dict[
        str, list[str]
    ]  # mapping of project_uuid and permissions


class AdminInfo(TypedDict):
    id: str
    username: str | None
    email: str | None
