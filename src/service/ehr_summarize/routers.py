from src.ehr.dtos import InputEHR
from src.shared.utils.logger import LOGGER
from src.shared.custom_types.responses import SSEResponse
from src.service.ehr_summarize.services import EHRSummaryService
from src.service.ehr_summarize.factories import getEhrSummaryService
from src.management.api_keys.dependencies import requiredPermissions

from typing import Annotated, TypedDict

from fastapi import Body, Depends, Security, APIRouter
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
    user_id: Annotated[str, Security(requiredPermissions(["placeholder"]))],
    ehr: InputEHR,
    ehr_service: Annotated[EHRSummaryService, Depends(getEhrSummaryService)],
    stream: bool = Body(False, embed=True),
):
    LOGGER.debug("user", user_id=user_id)
    if stream:
        return SSEResponse(ehr_service.summarize_ehr_stream(user_id, ehr))
    else:
        summary = await ehr_service.summarize_ehr(user_id, ehr)
        return JSONResponse({"summary": summary})
