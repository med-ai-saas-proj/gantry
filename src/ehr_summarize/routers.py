from src.auth import User, get_current_user
from src.ehr.dtos import InputEHR
from src.shared.utils.logger import LOGGER
from src.shared.custom_types.responses import SSEResponse

from .initialize import EHR_SUMMARY_SERVICE

from typing import Annotated, TypedDict

from fastapi import Body, Security, APIRouter
from fastapi.responses import JSONResponse


ehr_summarize_router = APIRouter(tags=["Doctor Help"])


class EHRSummary(TypedDict):
    summary: str


@ehr_summarize_router.post(
    "/ehr_summarize",
    response_model=EHRSummary,
    responses={
        200: {
            "content": {
                "stream/text-event": {},
            },
        }
    },
)
async def summarize_ehr(
    user: Annotated[User, Security(get_current_user)],
    ehr: InputEHR,
    stream: bool = Body(False, embed=True),
):
    LOGGER.debug("user", user_id=user["id"])
    if stream:
        return SSEResponse(
            EHR_SUMMARY_SERVICE.summarize_ehr_stream(user["id"], ehr)
        )
    else:
        summary = await EHR_SUMMARY_SERVICE.summarize_ehr(user["id"], ehr)
        return JSONResponse({"summary": summary})
