from gantry.settings import KeycloakSettings, getAppSettings


def getKeycloakSettings() -> KeycloakSettings:
    return getAppSettings().keycloak
