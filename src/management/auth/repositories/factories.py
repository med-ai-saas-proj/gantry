"""Repositories factory for the auth module."""

from .users import UserRepository
from .api_keys import ApiKeyRepository, PermissionRepository

from functools import lru_cache


@lru_cache(1)
def getUserRepository() -> UserRepository:
    """Get singleton instance of UserRepository."""
    return UserRepository()


@lru_cache(1)
def getApiKeyRepository() -> ApiKeyRepository:
    """Get singleton instance of ApiKeyRepository."""
    return ApiKeyRepository()


@lru_cache(1)
def getPermissionRepository() -> PermissionRepository:
    """Get singleton instance of PermissionRepository."""
    return PermissionRepository()
