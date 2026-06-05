from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.logger import LOGGER
from src.initialize.services import EHR_SUMMARY_SERVICE
from src.dtos.ehr import InputEHR
from src.custom_types.responses import SSEResponse
from src.services.ehr_summary import SSEContent


from pydantic import BaseModel
from typing import Annotated, TypedDict
from fastapi import APIRouter, Security, Body
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Doctor Help"])


class EHRSummary(TypedDict):
    summary: str


@router.post(
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
