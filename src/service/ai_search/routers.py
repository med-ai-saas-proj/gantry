from src.management.api_keys import requiredPermissions
from src.shared.utils.logger import LOGGER
from src.management.api_keys.entities import ApiKeyInfo
from src.shared.custom_types.responses.sse import SSEResponse

from .dtos import AiSearchInput
from .services import AiSearchService
from .factories import getAiSearchService
from ..utils.agent.dtos.model import ChatOutput, StreamEvent

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
    user: Annotated[ApiKeyInfo, Security(requiredPermissions(["placeholder"]))],
    input: AiSearchInput,
    ai_search_service: Annotated[AiSearchService, Depends(getAiSearchService)],
) -> SSEResponse | JSONResponse:
    """Use AI to search the internet and summarize the result."""
    user_id = user["user_id"]
    LOGGER.debug("user", user_id=user_id)
    if input.stream:
        return SSEResponse(
            ai_search_service.aiSearchStream(user_id, input.query),
        )
    else:
        output = await ai_search_service.aiSearch(user_id, input.query)
        return JSONResponse(output)
