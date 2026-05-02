"""Factory functions for the Keycloak module singletons."""

from gantry.keycloak import KeycloakServiceClient, getKeycloakSettings
from gantry.db.factories import getRedis, getSessionManager
from gantry.shared.logging.logger import getLogger
from gantry.management.auth.settings import getAuthSettings

from functools import lru_cache


@lru_cache(1)
def getKeycloakServiceClient(
    service_client_id: str, service_client_secret: str
) -> KeycloakServiceClient:
    """Singleton Keycloak Organisation client."""
    keycloak_settings = getKeycloakSettings()

    return KeycloakServiceClient(
        server_url=keycloak_settings.server_url.encoded_string(),
        realm=keycloak_settings.realm_name,
        service_client_id=service_client_id,
        service_client_secret=service_client_secret,
    )
