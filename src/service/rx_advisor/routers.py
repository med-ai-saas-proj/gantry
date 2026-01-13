from src.ehr.dtos import InputEHR, InputPrescription
from src.shared.utils.logger import LOGGER
from src.service.rx_advisor.factories import getRxAdvisorService
from src.shared.custom_types.responses import SSEResponse
from src.management.api_keys.dependencies import requiredPermissions

from .services import RxAdvisorService, GeneratedAnalysis

from typing import Annotated

from fastapi import Body, Depends, Security, APIRouter
from fastapi.responses import JSONResponse


rx_advisor_router = APIRouter(prefix="/rx_advisor", tags=["Doctor Help"])



@rx_advisor_router.post(
    "",
    response_model=GeneratedAnalysis,
    responses={
        200: {
            "content": {
                "stream/text-event": {},
            },
        }
    },
)
async def rx_advisor(
    user_id: Annotated[str, Security(requiredPermissions(["placeholder"]))],
    ehr: InputEHR,
    prescription: InputPrescription,
    rx_advisor_service: Annotated[RxAdvisorService, Depends(getRxAdvisorService)],
    stream: bool = Body(False, embed=True),
):
    LOGGER.debug("user", user_id=user_id)
    if stream:
        return SSEResponse(
            rx_advisor_service.generate_advice_stream(
                user_id, ehr, prescription
            ),
        )
    else:
        analysis = await rx_advisor_service.generate_advice(
            user_id, ehr, prescription
        )
        return JSONResponse(analysis)
