from gantry.settings import ApiGatewaySettings, getAppSettings


def getApiGatewaySettings() -> ApiGatewaySettings:
    return getAppSettings().api_gateway
