"""Dynamic API key permission registry."""

from typing import Final


_REGISTERED_PERMISSIONS: Final[set[str]] = set()
_REGISTRATION_DONE = False


def registerPermissions(permissions: list[str]) -> None:
    """Register dynamic permissions declared by API-key-protected routes."""
    global _REGISTRATION_DONE
    normalized = {
        permission
        for permission in permissions
        if isinstance(permission, str) and permission
    }
    if _REGISTRATION_DONE and not normalized.issubset(_REGISTERED_PERMISSIONS):
        raise RuntimeError(
            "API key permissions were already finalized; cannot register new permissions."
        )
    _REGISTERED_PERMISSIONS.update(normalized)


def doneRegisterPermission() -> None:
    """Finalize the permission catalog after all protected routes are loaded."""
    global _REGISTRATION_DONE
    _REGISTRATION_DONE = True


def isPermissionRegistrationDone() -> bool:
    """Return whether the dynamic permission registry has been finalized."""
    return _REGISTRATION_DONE


def listPermissions() -> list[str]:
    """Return all registered permissions in stable order."""
    return sorted(_REGISTERED_PERMISSIONS)


def hasOnlyRegisteredPermissions(permissions: list[str]) -> bool:
    """Check whether every permission is known to the registry."""
    return all(
        permission in _REGISTERED_PERMISSIONS for permission in permissions
    )


def clearPermissions() -> None:
    """Reset the registry for unit tests."""
    global _REGISTRATION_DONE
    _REGISTERED_PERMISSIONS.clear()
    _REGISTRATION_DONE = False
