from pyrusult import Ok, Err, Result
from gantry.settings import ApiGatewayRoute
from gantry.shared.custom_types.error_exception import RecoverableError

from structlog.stdlib import BoundLogger


class RouteNotFoundError(RecoverableError):
    status = 404
    code = "route_not_found"
    title = "Route Not Found"
    detail = "The requested gateway route does not exist."


class GatewayUpstreamError(RecoverableError):
    status = 502
    code = "upstream_error"
    title = "Upstream Error"
    detail = "Failed to communicate with the upstream service."


class InsufficientPermission(RecoverableError):
    status = 403
    code = "api_key_insufficient_permission"
    title = "Insufficient Permission"
    detail = "Api key does not have required permission"


class ApiGatewayService:
    def __init__(
        self,
        logger: BoundLogger,
        routes: dict[str, ApiGatewayRoute],
    ):
        self.logger = logger
        self.routes = routes

    def getDestination(
        self, route_name: str
    ) -> Result[ApiGatewayRoute, RouteNotFoundError]:
        res = self.routes.get(route_name)
        if res is None:
            return Err(RouteNotFoundError())
        return Ok(res)

    def checkPermission(
        self, apikey_permission, route: ApiGatewayRoute
    ) -> Result[None, InsufficientPermission]:
        if set(apikey_permission).issuperset(route.required_perms):
            return Ok(None)
        return Err(InsufficientPermission())
