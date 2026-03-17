from typing import TypedDict, NotRequired


class UserInfo(TypedDict):
    id: str
    username: str | None
    email: str | None
    roles: list[str]
    org_id: str
