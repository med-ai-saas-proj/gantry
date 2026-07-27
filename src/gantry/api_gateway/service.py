from pyrusult import Ok, Err, Result
from gantry.settings import ApiGatewayRoute
from gantry.shared.custom_types.error_exception import RecoverableError

from limits import RateLimitItemPerMinute
from limits.aio import storage, strategies
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


class DocNotFound(RecoverableError):
    code = "doc_not_found"
    status = 404
    title = "Document for this service does not exist."
    delail = "Document for this service does not exist."


class ServiceOverloaded(RecoverableError):
    status = 429
    code = "service_overloaded"
    title = "Service Overloaded"
    detail = "The service is overloaded. Please try again later."


class ApiGatewayService:
    def __init__(
        self,
        logger: BoundLogger,
        routes: dict[str, ApiGatewayRoute],
        limit_storage: storage.Storage,
    ):
        self.logger = logger
        self.routes = routes
        self.limit_storage = limit_storage
        self.limiter = strategies.MovingWindowRateLimiter(self.limit_storage)

    def getDestination(
        self, route_name: str
    ) -> Result[ApiGatewayRoute, RouteNotFoundError | ServiceOverloaded]:
        res = self.routes.get(route_name)
        if res is None:
            return Err(RouteNotFoundError())
        if res.rate_limit is not None:
            limit = RateLimitItemPerMinute(res.rate_limit)
            if self.limiter.hit(limit, "api_gateway", route_name):
                return Err(ServiceOverloaded())
        return Ok(res)

    def checkPermission(
        self, apikey_permission, route: ApiGatewayRoute
    ) -> Result[None, InsufficientPermission]:
        if set(apikey_permission).issuperset(route.required_perms):
            return Ok(None)
        return Err(InsufficientPermission())
