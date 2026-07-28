from gantry.shared.dependencies import getOptionalProjectId

from .dtos import RunAgentInputWithModelSettings
from .services import AiGatewayService
from .factories import getAiGatewayService

from typing import Annotated

from fastapi import Body, Path, Depends, APIRouter
from ag_ui.core import Event
from fastapi.sse import EventSourceResponse


ai_gateway_router = APIRouter(prefix="/ai-gateway", tags=["ai-gateway"])
ai_gateway_public_router = APIRouter(prefix="/ai-gateway", tags=["ai-gateway"])


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
    ai_gateway_service: Annotated[
        AiGatewayService, Depends(getAiGatewayService)
    ],
    model: Annotated[str, Path()],
    run_input: Annotated[RunAgentInputWithModelSettings, Body(embed=False)],
    project_id: Annotated[int | None, Depends(getOptionalProjectId)] = None,
):

    model_settings = run_input.model_settings or {}
    if project_id is not None:
        return EventSourceResponse(
            (
                await ai_gateway_service.route(
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
    return EventSourceResponse(
        (
            await ai_gateway_service.route(
                model,
                None,
                run_input,
                model_settings,
                system_prompt=run_input.system_prompt,
                max_turns=run_input.max_turns or 100,
                reserved_tokens=run_input.reserved_tokens or 0,
            )
        ).unwrap()
    )
