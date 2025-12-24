from src.ehr.dtos import InputEHR, InputPrescription
from src.shared.utils.logger import LOGGER
from src.service.rx_advisor.factories import getRxAdvisorService
from src.shared.custom_types.responses import SSEResponse
from src.management.api_keys.dependencies import requiredPermissions

from .services import ModelInput, RxAdvisorService

from typing import Annotated

from fastapi import Depends, Security, APIRouter


rx_advisor_router = APIRouter(prefix="/rx_advisor", tags=["Doctor Help"])


@rx_advisor_router.post(
    "/",
    responses={
        200: {
            "content": {
                "stream/text-event": {},
            },
        }
    },
)
async def rx_advisor(
    # user_id: Annotated[str, Security(requiredPermissions(["placeholder"]))],
    ehr: InputEHR,
    prescription: InputPrescription,
    rx_advisor_service: Annotated[
        RxAdvisorService, Depends(getRxAdvisorService)
    ],
):
    user_id = "testuser"
    LOGGER.debug("user", user_id=user_id)
    return SSEResponse(
        rx_advisor_service.generateAgentResponse(
            user_id, ModelInput(ehr=ehr, prescription=prescription)
        ),
    )
