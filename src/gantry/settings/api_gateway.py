from __future__ import annotations

from typing import Self, Annotated

from pydantic import Field, BaseModel, model_validator


class ApiGatewayPermission(BaseModel):
    id: Annotated[
        str,
        Field(description="Unique permission identifier."),
    ]
    name: Annotated[
        str,
        Field(description="Human-readable permission name."),
    ]
    description: Annotated[
        str,
        Field(
            description="Explanation of what this permission grants.",
        ),
    ]


class ApiGatewayRoute(BaseModel):
    address: Annotated[
        str,
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
    auto_hold: Annotated[
        int | None,
        Field(
            description="Credits to hold automatically per request.",
        ),
    ] = None
    auto_charge: Annotated[
        int | None,
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


class ApiGatewaySettings(BaseModel):
    permissions: Annotated[
        list[ApiGatewayPermission],
        Field(description="Available API gateway permissions."),
    ] = []
    routes: Annotated[
        dict[str, ApiGatewayRoute],
        Field(description="Route definitions keyed by route name."),
    ] = {}

    @model_validator(mode="after")
    def validate_required_perms(self) -> Self:
        permission_ids = {p.id for p in self.permissions}
        for route_name, route in self.routes.items():
            if route.required_perms is None:
                continue
            invalid = set(route.required_perms) - permission_ids
            if invalid:
                raise ValueError(
                    f"Route '{route_name}' has unknown "
                    f"permission(s): {sorted(invalid)}"
                )
        return self
