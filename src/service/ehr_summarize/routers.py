from src.shared.utils.logger import LOGGER
from src.management.api_keys.entities import ApiKeyInfo
from src.shared.custom_types.responses import SSEResponse
from src.service.ehr_summarize.factories import getEHRSummarizeService
from src.management.api_keys.dependencies import requiredPermissions

from .dtos import EHRSummarizeInput
from .factories import EHRSummarizeService
from ..utils.agent.dtos.model import ChatOutput, StreamEvent

from typing import Annotated

from fastapi import Depends, Security, APIRouter
from fastapi.responses import JSONResponse


ehr_summarize_router = APIRouter(tags=["Doctor Help"])


@ehr_summarize_router.post(
    "/ehr_summarize",
    response_model=ChatOutput | StreamEvent,
    responses={
        200: {
            "content": {
                "stream/text-event": {},
            },
        }
    },
)
async def summarize_ehr(
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    input: EHRSummarizeInput,
    ehr_summarize_service: Annotated[
        EHRSummarizeService, Depends(getEHRSummarizeService)
    ],
):
    LOGGER.debug("api_key_info", api_key_info=api_key_info)
    if input.stream:
        return SSEResponse(
            ehr_summarize_service.summarizeStream(
                api_key_info, input.model, input.input_ehr
            )
        )
    else:
        summary = await ehr_summarize_service.summarize(
            api_key_info, input.model, input.input_ehr
        )
        return JSONResponse(summary)
