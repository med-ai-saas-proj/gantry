"""Factory functions for creating service instances."""

from gantry.keycloak import getKeycloakSettings, getKeycloakServiceClient

from .services import AuthService
from .settings import getAuthSettings

from functools import lru_cache


@lru_cache(1)
def getAuthService() -> AuthService:
    """Get singleton AuthService instance."""
    auth_settings = getAuthSettings()
    keycloak_settings = getKeycloakSettings()
    return AuthService(
        server_url=keycloak_settings.server_url.encoded_string(),
        realm=keycloak_settings.realm_name,
        client_id=auth_settings.client_id,
        keycloak_client=getKeycloakServiceClient(),
        forbidden_realm_roles={AuthService.ADMIN_REALM_ROLE},
        issuer_url=(
            keycloak_settings.issuer_url.encoded_string()
            if keycloak_settings.issuer_url
            else None
        ),
        jwks_url=(
            keycloak_settings.jwks_url.encoded_string()
            if keycloak_settings.jwks_url
            else None
        ),
    )


@lru_cache(1)
def getAuthServiceWithoutOrg() -> AuthService:
    """Get user AuthService for onboarding flows before org membership exists."""
    auth_settings = getAuthSettings()
    keycloak_settings = getKeycloakSettings()
    return AuthService(
        server_url=keycloak_settings.server_url.encoded_string(),
        realm=keycloak_settings.realm_name,
        client_id=auth_settings.client_id,
        keycloak_client=getKeycloakServiceClient(),
        require_organization_claim=False,
        forbidden_realm_roles={AuthService.ADMIN_REALM_ROLE},
        issuer_url=(
            keycloak_settings.issuer_url.encoded_string()
            if keycloak_settings.issuer_url
            else None
        ),
        jwks_url=(
            keycloak_settings.jwks_url.encoded_string()
            if keycloak_settings.jwks_url
            else None
        ),
    )


@lru_cache(1)
def getAdminAuthService() -> AuthService:
    """Get singleton AuthService instance for admin users."""
    keycloak_settings = getKeycloakSettings()
    auth_settings = getAuthSettings()
    return AuthService(
        server_url=keycloak_settings.server_url.encoded_string(),
        realm=keycloak_settings.realm_name,
        client_id=auth_settings.admin_client_id,
        keycloak_client=getKeycloakServiceClient(),
        require_organization_claim=False,
        issuer_url=(
            keycloak_settings.issuer_url.encoded_string()
            if keycloak_settings.issuer_url
            else None
        ),
        jwks_url=(
            keycloak_settings.jwks_url.encoded_string()
            if keycloak_settings.jwks_url
            else None
        ),
    )
