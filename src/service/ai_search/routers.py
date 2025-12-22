from src.shared.utils.logger import LOGGER
from src.service.ai_search.services import AISearchService
from src.service.ai_search.factories import getAISearchService
from src.management.api_keys.dependencies import requiredPermissions
from src.shared.custom_types.responses.sse import SSEResponse

from .dtos import AiSearchInput
from ..chat.dtos import ChatOutput, StreamEvent

from typing import Annotated

from fastapi import Depends, Security, APIRouter
from fastapi.responses import JSONResponse


ai_search_router = APIRouter(prefix="/ai_search", tags=["Doctor Help"])


@ai_search_router.post(
    "",
    response_model=ChatOutput | StreamEvent,
    responses={
        200: {
            "content": {
                "stream/text-event": {},
                "application/json": {},
            },
        },
    },
)
async def ai_search(
    user_id: Annotated[str, Security(requiredPermissions(["placeholder"]))],
    ai_search_service: Annotated[AISearchService, Depends(getAISearchService)],
    input: AiSearchInput,
) -> SSEResponse | JSONResponse:
    """Use AI to search the internet and summarize the result."""
    LOGGER.debug("user", user_id=user_id)
    if input.stream:
        return SSEResponse(
            ai_search_service.ai_search_stream(user_id, input.query),
        )
    else:
        output = await ai_search_service.ai_search(user_id, input.query)
        return JSONResponse(output)
