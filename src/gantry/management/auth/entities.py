from typing import TypedDict


class UserInfo(TypedDict):
    id: str
    username: str | None
    email: str | None
    roles: list[str]
    org_id: str
    project_uids: list[str]
