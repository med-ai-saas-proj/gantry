from gantry.settings import AiGatewaySettings, getAppSettings


def getAIGatewaySettings() -> AiGatewaySettings:
    return getAppSettings().ai_gateway
