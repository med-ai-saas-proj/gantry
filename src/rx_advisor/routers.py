from src.ehr.dtos import InputEHR, InputPrescription
from src.auth.depends.auth import get_current_user
from src.shared.utils.logger import LOGGER
from src.auth.entities.auth_info import AuthInfo as User
from src.shared.custom_types.responses import SSEResponse

from .services import GeneratedAnalysis
from .initialize import RX_ADVISOR_SERVICE

from typing import Annotated

from fastapi import Body, Security, APIRouter
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
