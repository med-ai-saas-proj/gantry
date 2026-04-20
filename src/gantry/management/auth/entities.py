from typing import TypedDict, NotRequired


class AccessibleProjectInfo(TypedDict):
    """Project metadata attached to authenticated management users."""

    id: str
    name: str
    description: str | None
    organization_id: str
    archived: bool


class UserInfo(TypedDict):
    id: str
    username: str | None
    email: str | None
    roles: list[str]
    org_id: str
    projects: NotRequired[list[AccessibleProjectInfo]]
