from gantry.management.api_key import ApiKeyInfo, getApiKeyInfo

from .services import AiGatewayService
from .factories import getAiGatewayService

from typing import Any, Literal, Annotated, TypedDict

from fastapi import Body, Path, Depends, APIRouter
from ag_ui.core import Event, RunAgentInput
from fastapi.sse import EventSourceResponse
from pydantic_ai import ModelSettings


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


class RunAgentInputWithModelSettings(RunAgentInput):
    model_settings: ModelSettingsInput | None = None


@ai_gateway_router.post(
    "/ag-ui/{model}",
    response_model=Event,
    response_class=EventSourceResponse,
)
async def ag_ui_gateway(
    api_key_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo)],
    ai_gateway_service: Annotated[
        AiGatewayService, Depends(getAiGatewayService)
    ],
    model: Annotated[str, Path()],
    run_input: Annotated[RunAgentInputWithModelSettings, Body(embed=False)],
):
    model_settings = run_input.model_settings or {}
    return (
        await ai_gateway_service.ficl(
            model, api_key_info["project_id"], run_input, model_settings
        )
    ).unwrap()
