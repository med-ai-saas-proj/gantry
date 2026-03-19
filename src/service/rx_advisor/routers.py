from src.shared.logging.logger import LOGGER
from src.management.api_keys.entities import ApiKeyInfo
from src.shared.custom_types.responses import SSEResponse
from src.management.api_keys.dependencies import requiredPermissions

from .dtos import RxAdvisorInput
from .services import RxAdvisorService
from .factories import getRxAdvisorService
from ..utils.agent.dtos.model import ChatOutput, StreamEvent

from typing import Annotated

from fastapi import Depends, Security, APIRouter
from fastapi.responses import JSONResponse


rx_advisor_router = APIRouter(prefix="/rx_advisor", tags=["Doctor Help"])


@rx_advisor_router.post(
    "",
    response_model=ChatOutput | StreamEvent,
    responses={
        200: {
            "content": {
                "stream/text-event": {},
            },
        }
    },
)
async def rx_advisor(
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    input: RxAdvisorInput,
    rx_advisor_service: Annotated[
        RxAdvisorService, Depends(getRxAdvisorService)
    ],
):
    LOGGER.debug("api_key_info", api_key_info=api_key_info)
    if input.stream:
        return SSEResponse(
            rx_advisor_service.generateAdviceStream(
                api_key_info, input.model, input.ehr, input.prescription
            ),
        )
    else:
        analysis = await rx_advisor_service.generateAdvice(
            api_key_info, input.model, input.ehr, input.prescription
        )
        return JSONResponse(analysis)
