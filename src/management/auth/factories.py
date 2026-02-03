"""Factory functions for creating service instances."""

from functools import lru_cache

from .services import AuthService
from .settings import getAuthSettings


@lru_cache(1)
def getAuthService() -> AuthService:
    """Get singleton AuthService instance."""
    settings = getAuthSettings()
    return AuthService(
        server_url=settings.server_url.encoded_string,
        realm=settings.realm_name,
        client_id=settings.client_id,
    )
