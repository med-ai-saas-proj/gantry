from .services import KeycloakService
from .settings import getAuthSettings

from functools import lru_cache


@lru_cache(1)
def getKeycloakService():
    settings = getAuthSettings()
    return KeycloakService(
        server_url=settings.server_url.encoded_string(),
        realm=settings.realm_name,
        client_id=settings.client_id,
    )
