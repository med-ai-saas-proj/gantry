"""Project permission definitions."""

from enum import Enum
from typing import Final


class ProjectPermission(str, Enum):
    """Fine-grained project permissions."""

    OWNER = "project.owner"

    MEMBER = "project.member"

    USERS_ADD = "project.users.add"
    USERS_GET_ALL = "project.users.get_all"
    USERS_REMOVE = "project.users.remove"
    USERS_PERMISSIONS_RW = "project.users.permissions.read_write"

    SETTINGS_READ = "project.settings.read"
    SETTINGS_WRITE = "project.settings.write"

    APIKEY_READ = "apikey.read"
    APIKEY_WRITE = "apikey.write"

    RAG_MANAGE = "project.rag.manage"
    FILE_STORAGE_MANAGE = "project.file_storage.manage"


PERMISSION_HIERARCHY: Final[
    dict[ProjectPermission, list[ProjectPermission]]
] = {
    ProjectPermission.OWNER: [
        ProjectPermission.USERS_ADD,
        ProjectPermission.USERS_GET_ALL,
        ProjectPermission.USERS_REMOVE,
        ProjectPermission.USERS_PERMISSIONS_RW,
        ProjectPermission.SETTINGS_READ,
        ProjectPermission.SETTINGS_WRITE,
        ProjectPermission.APIKEY_READ,
        ProjectPermission.APIKEY_WRITE,
        ProjectPermission.RAG_MANAGE,
    ]
}


ALL_PERMISSIONS: Final[list[str]] = [p.value for p in ProjectPermission]
PROJECT_PERMISSIONS_ATTR: Final[str] = "project_permissions"


def get_effective_permissions(user_permissions: list[str]) -> set[str]:
    """Expand raw permission list using hierarchy."""
    effective = set(user_permissions)
    for perm_str in user_permissions:
        try:
            perm = ProjectPermission(perm_str)
        except ValueError:
            continue
        children = PERMISSION_HIERARCHY.get(perm, [])
        effective.update(c.value for c in children)
    return effective


def has_permission(
    user_permissions: list[str] | None,
    required: ProjectPermission,
) -> bool:
    """Check whether user has required project permission."""
    if not user_permissions:
        return False
    return required.value in get_effective_permissions(user_permissions)
