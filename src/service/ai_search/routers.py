from src.shared.utils.logger import LOGGER
from src.management.api_keys.dependencies import requiredPermission
from src.shared.custom_types.responses.sse import SSEResponse

from .dtos import AiSearchInput
from .initialize import AI_SEARCH_SERVICE
from ..chat.dtos import ChatOutput, StreamEvent

from typing import Annotated

from fastapi import Security, APIRouter
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
    user_id: Annotated[str, Security(requiredPermission(["placeholder"]))],
    input: AiSearchInput,
) -> SSEResponse | JSONResponse:
    """Use AI to search the internet and summarize the result."""
    LOGGER.debug("user", user_id=user_id)
    if input.stream:
        return SSEResponse(
            AI_SEARCH_SERVICE.ai_search_stream(user_id, input.query),
        )
    else:
        output = await AI_SEARCH_SERVICE.ai_search(user_id, input.query)
        return JSONResponse(output)
