from gantry.management.api_key.permissions import registerPermissions

from .routes import gateway_router
from .settings import getApiGatewaySettings


settings = getApiGatewaySettings()
registerPermissions([p.id for p in settings.permissions])
