from typing import Annotated
from fastapi import APIRouter, Security, Body
from fastapi.responses import JSONResponse

from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.logger import LOGGER
from src.initialize.services import RX_ADVISOR_SERVICE
from src.services.rx_advisor import GeneratedAnalysis
from src.dtos.ehr import InputEHR, InputPrescription
from src.custom_types.responses import SSEResponse


router = APIRouter(tags=["Doctor Help"])


@router.post(
    "/rx_advisor",
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
    user: Annotated[User, Security(get_current_user)],
    ehr: InputEHR,
    prescription: InputPrescription,
    stream: bool = Body(False, embed=True),
):
    LOGGER.debug("user", user_id=user["id"])
    if stream:
        return SSEResponse(
            RX_ADVISOR_SERVICE.generate_advice_stream(
                user["id"], ehr, prescription
            ),
        )
    else:
        analysis = await RX_ADVISOR_SERVICE.generate_advice(
            user["id"], ehr, prescription
        )
        return JSONResponse(analysis)
