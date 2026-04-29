"""Factory functions for creating service instances."""

from .services import AuthService
from .settings import getAuthSettings

from functools import lru_cache


@lru_cache(1)
def getAuthService() -> AuthService:
    """Get singleton AuthService instance."""
    settings = getAuthSettings()
    return AuthService(
        server_url=settings.server_url.encoded_string(),
        realm=settings.realm_name,
        client_id=settings.client_id,
    )


@lru_cache(1)
def getAdminAuthService() -> AuthService:
    """Get singleton AuthService instance for admin users."""
    settings = getAuthSettings()
    return AuthService(
        server_url=settings.server_url.encoded_string(),
        realm=settings.realm_name,
        client_id=settings.admin_client_id,
        require_organization_claim=False,
    )
