from src.ehr.custom_types import EHRFormat
from src.shared.utils.logger import LOGGER
from src.management.api_keys.entities import ApiKeyInfo
from src.management.api_keys.dependencies import requiredPermissions
from src.shared.custom_types.responses.sse import SSEResponse

from .dtos import OCROutput

# from .dtos import AiSearchInput
# from .initialize import AI_SEARCH_SERVICE
from ..utils.agent.dtos.model import StreamEvent

from typing import Annotated

from fastapi import File, Query, Security, APIRouter, UploadFile
from fastapi.responses import JSONResponse
from typing_extensions import Literal


ocr_router = APIRouter(prefix="/ocr", tags=["Doctor Help"])


@ocr_router.post(
    "",
    response_model=OCROutput | StreamEvent,
    responses={
        200: {
            "content": {
                "stream/text-event": {},
                "application/json": {},
            },
        },
    },
)
async def ocr(
    user_id: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    image: Annotated[UploadFile, File(title="Image to OCR.")],
    format: Annotated[EHRFormat, Query(title="Output format")],
) -> SSEResponse | JSONResponse:
    """Use AI to OCR and structure the text into specified format."""
    # LOGGER.debug("user", user_id=user_id)
    # if input.stream:
    #     return SSEResponse(
    #         AI_SEARCH_SERVICE.ai_search_stream(user_id, input.query),
    #     )
    # else:
    #     output = await AI_SEARCH_SERVICE.ai_search(user_id, input.query)
    #     return JSONResponse(output)
    pass
