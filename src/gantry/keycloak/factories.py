"""Factory functions for the Keycloak module singletons."""

from gantry.keycloak import KeycloakServiceClient, getKeycloakSettings

from functools import lru_cache


@lru_cache(1)
def getKeycloakServiceClient() -> KeycloakServiceClient:
    """Singleton Keycloak Organisation client."""
    keycloak_settings = getKeycloakSettings()

    return KeycloakServiceClient(
        server_url=keycloak_settings.server_url.encoded_string(),
        realm=keycloak_settings.realm_name,
        service_client_id=keycloak_settings.service_client_id,
        service_client_secret=keycloak_settings.service_client_secret,
    )
