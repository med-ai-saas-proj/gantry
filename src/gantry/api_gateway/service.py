from gantry.settings import ApiGatewayRoute
from gantry.shared.custom_types.error_exception import RecoverableError

from pyrusult import Ok, Err, Result
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

    # async def handle(
    #     self,
    #     route_name: str,
    #     request: Request,
    # ) -> Response:
    #     settings = getApiGatewaySettings()

    #     # 1. Check if route exists
    #     route = settings.routes.get(route_name)
    #     if route is None:
    #         raise RouteNotFoundError()

    #     # 2. Check route rate limit
    #     if route.rate_limit is not None:
    #         route_key = f"gw:rl:route:{route_name}"
    #         allowed = await self._checkRateLimit(route_key, route.rate_limit)
    #         if not allowed:
    #             raise RouteRateLimitExceeded()

    #     # 3. Validate API key
    #     api_key_header = request.headers.get("X-Api-Key")
    #     if api_key_header is None:
    #         raise InvalidAPIKey()

    #     context_res = await self.api_key_service._resolveApiKeyContext(
    #         api_key_header
    #     )
    #     _, context = context_res.unwrap()

    #     if context["disabled"]:
    #         raise ApiKeyDisabledError()
    #     if not context["user_uuid"]:
    #         raise UserNotFoundError()

    #     # 4. Check API key rate limit (org + project)
    #     org_rpm = context["rpm_limit_organization"]
    #     project_rpm = context["rpm_limit_project"]

    #     if org_rpm != -1:
    #         org_key = f"gw:rl:org:{context['organization_uuid']}"
    #         if not await self._checkRateLimit(org_key, org_rpm):
    #             raise ApiKeyRateLimitExceeded()

    #     if project_rpm != -1:
    #         project_key = f"gw:rl:project:{context['project_uuid']}"
    #         if not await self._checkRateLimit(project_key, project_rpm):
    #             raise ApiKeyRateLimitExceeded()

    #     # 5. Spending limit is checked by TransactionService.post
    #     # when auto_hold or auto_charge is configured.

    #     # 6. Check API key permissions
    #     if route.required_perms:
    #         existing_perms = set(context["permissions"])
    #         missing = set(route.required_perms) - existing_perms
    #         if missing:
    #             raise GatewayPermissionDenied()

    #     # 7. Hold if auto_hold
    #     transaction_uid: UUID | None = None
    #     if route.auto_hold is not None:
    #         hold_amount: ScaledAmount = {
    #             "value": route.auto_hold,
    #             "scale": 0,
    #         }
    #         hold_result = await self.transaction_service.post(
    #             org_id=context["organization_uuid"],
    #             project_id=context["project_id"],
    #             api_key_id=context["api_key_id"],
    #             idempotency_key=None,
    #             req=PostRequest(
    #                 amount=hold_amount,
    #                 capture=False,
    #             ),
    #         )
    #         transaction_uid = hold_result.unwrap()

    #     # 8. Forward request
    #     response = await self._forwardRequest(request, route.address, context)

    #     # 9. Charge if auto_charge
    #     if route.auto_charge is not None:
    #         charge_amount: ScaledAmount = {
    #             "value": route.auto_charge,
    #             "scale": 0,
    #         }
    #         if transaction_uid is not None:
    #             await self.transaction_service.capture(
    #                 org_id=context["organization_uuid"],
    #                 project_id=context["project_id"],
    #                 api_key_id=context["api_key_id"],
    #                 transaction_uid=transaction_uid,
    #                 real_amount=charge_amount,
    #             )
    #         else:
    #             await self.transaction_service.post(
    #                 org_id=context["organization_uuid"],
    #                 project_id=context["project_id"],
    #                 api_key_id=context["api_key_id"],
    #                 idempotency_key=None,
    #                 req=PostRequest(
    #                     amount=charge_amount,
    #                     capture=True,
    #                 ),
    #             )

    #     return response

    # async def _forwardRequest(
    #     self,
    #     request: Request,
    #     upstream_address: str,
    #     context: ApiKeyContextRecord,
    # ) -> Response:
    #     body = await request.body()

    #     forwarded_headers = dict(request.headers)
    #     forwarded_headers.pop("host", None)
    #     forwarded_headers.pop("x-api-key", None)
    #     forwarded_headers["X-Organization-UUID"] = context["organization_uuid"]
    #     forwarded_headers["X-Project-UUID"] = context["project_uuid"]
    #     forwarded_headers["X-API-Key-UUID"] = context["api_key_uuid"]

    #     try:
    #         upstream_resp = await self.http_client.request(
    #             method=request.method,
    #             url=upstream_address,
    #             headers=forwarded_headers,
    #             content=body,
    #             params=dict(request.query_params),
    #         )
    #     except httpx.HTTPError as exc:
    #         self.logger.error(
    #             "gateway.upstream_error",
    #             upstream=upstream_address,
    #             error=str(exc),
    #         )
    #         raise GatewayUpstreamError()

    #     excluded_headers = {
    #         "content-encoding",
    #         "content-length",
    #         "transfer-encoding",
    #         "connection",
    #     }
    #     response_headers = {
    #         k: v
    #         for k, v in upstream_resp.headers.items()
    #         if k.lower() not in excluded_headers
    #     }

    #     return Response(
    #         content=upstream_resp.content,
    #         status_code=upstream_resp.status_code,
    #         headers=response_headers,
    #     )
