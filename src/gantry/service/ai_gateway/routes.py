from .services import AiGatewayService
from .factories import getAiGatewayService

from uuid import UUID
from typing import Literal, Annotated, TypedDict

from fastapi import Body, Path, Query, Depends, APIRouter
from ag_ui.core import Event, RunAgentInput
from fastapi.sse import EventSourceResponse


class ModelSettingsInput(
    TypedDict,
    total=False,
):
    max_tokens: int
    temperature: float
    top_p: float
    timeout: float
    parallel_tool_calls: bool
    seed: int
    presence_penalty: float
    frequency_penalty: float
    logit_bias: dict[str, int]
    stop_sequences: list[str]
    thinking: bool | Literal["minimal", "low", "medium", "high", "xhigh"]
    service_tier: Literal["auto", "default", "flex", "priority"]


ai_gateway_router = APIRouter(prefix="/ai-gateway", tags=["ai-gateway"])
ai_gateway_public_router = APIRouter(prefix="/ai-gateway", tags=["ai-gateway"])


class RunAgentInputWithModelSettings(RunAgentInput):
    model_settings: ModelSettingsInput | None = None
    system_prompt: str | list[str] | None = None
    max_turns: int | None = None
    reserved_tokens: int | None = None


@ai_gateway_router.get("/models")
@ai_gateway_public_router.get("/models")
async def get_models(
    ai_gateway_service: Annotated[
        AiGatewayService, Depends(getAiGatewayService)
    ],
) -> list[str]:
    return ai_gateway_service.getModels()


@ai_gateway_router.post(
    "/ag-ui/{model}",
    response_model=Event,
    # response_class=EventSourceResponse,
)
async def ag_ui_gateway(
    project_id: Annotated[UUID, Query()],
    ai_gateway_service: Annotated[
        AiGatewayService, Depends(getAiGatewayService)
    ],
    model: Annotated[str, Path()],
    run_input: Annotated[RunAgentInputWithModelSettings, Body(embed=False)],
):

    model_settings = run_input.model_settings or {}
    return EventSourceResponse(
        (
            await ai_gateway_service.routeWithProjectUUID(
                model,
                project_id,
                run_input,
                model_settings,
                system_prompt=run_input.system_prompt,
                max_turns=run_input.max_turns or 100,
                reserved_tokens=run_input.reserved_tokens or 0,
            )
        ).unwrap()
    )
