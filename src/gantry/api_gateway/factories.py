from gantry.shared.logging.logger import getLogger

from .service import ApiGatewayService
from .settings import getApiGatewaySettings

from functools import lru_cache


@lru_cache(1)
def getApiGatewayService() -> ApiGatewayService:
    return ApiGatewayService(getLogger(), getApiGatewaySettings().routes)
