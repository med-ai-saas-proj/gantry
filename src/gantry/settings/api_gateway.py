from gantry.shared.utils.scaled_amount import ScaledAmount

from typing import Annotated
from datetime import timedelta

from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings


class ApiGatewayRoute(BaseSettings):
    address: Annotated[
        AnyUrl,
        Field(
            description="Upstream service address for this route.",
        ),
    ]
    required_perms: Annotated[
        list[str],
        Field(
            description="Permission IDs required to access this route.",
        ),
    ] = []
    openapi_json_url: Annotated[
        AnyUrl | None,
        Field(description="Open API json url, uses for docs in frontend"),
    ] = None
    auto_charge: Annotated[
        ScaledAmount | None,
        Field(
            description="Credits to charge automatically per request.",
        ),
    ] = None
    rate_limit: Annotated[
        int | None,
        Field(
            description="Maximum requests per minute for this route.",
        ),
    ] = None


class ApiGatewaySettings(BaseSettings):
    routes: Annotated[
        dict[str, ApiGatewayRoute],
        Field(description="Route definitions keyed by route name."),
    ] = {}
    request_timeout: Annotated[
        timedelta, Field(description="Timeout for proxy request")
    ] = timedelta(seconds=30)

    # @model_validator(mode="after")
    # def validate_required_perms(self) -> Self:
    #     permission_ids = {p.id for p in self.permissions}
    #     for route_name, route in self.routes.items():
    #         if route.required_perms is None:
    #             continue
    #         invalid = set(route.required_perms) - permission_ids
    #         if invalid:
    #             raise ValueError(
    #                 f"Route '{route_name}' has unknown "
    #                 f"permission(s): {sorted(invalid)}"
    #             )
    #     return self
