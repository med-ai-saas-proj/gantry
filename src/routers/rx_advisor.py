from typing import Annotated, Any, AsyncGenerator, TypedDict, NotRequired
from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse, JSONResponse

from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.logger import LOGGER
from src.utils.response import ResponseUtils
from src.initialize.services import RX_ADVISOR_SERVICE
from src.dtos.ehr import InputEHR, InputPrescription


router = APIRouter(tags=["Doctor Help"])


async def stream_summary(generator: AsyncGenerator[str, None]):
    async for delta in generator:
        data = {"d": delta}
        yield ResponseUtils.format_sse("delta", data)


@router.post("/rx_advisor")
async def rx_advisor(
    user: Annotated[User, Depends(get_current_user)],
    ehr: InputEHR,
    prescription: InputPrescription,
    stream: bool = Body(False, embed=True),
):
    LOGGER.debug("user", user_id=user["id"])
    if stream:
        return StreamingResponse(
            stream_summary(
                RX_ADVISOR_SERVICE.generate_advice_stream(
                    user["id"], ehr, prescription
                )
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )
    else:
        analysis = await RX_ADVISOR_SERVICE.generate_advice(
            user["id"], ehr, prescription
        )
        return JSONResponse({"analysis": analysis})
