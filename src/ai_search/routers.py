from src.chat.dtos import ChatOutput, StreamEvent
from src.auth.security import get_current_user
from src.auth.entities.user import User
from src.shared.utils.logger import LOGGER
from src.shared.custom_types.responses.sse import SSEContent, SSEResponse

from .dtos import AiSearchInput
from .initialize import AI_SEARCH_SERVICE

from typing import Any, Annotated, AsyncGenerator

from fastapi import Body, Security, APIRouter
from pydantic import TypeAdapter
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
    user: Annotated[User, Security(get_current_user)], input: AiSearchInput
) -> SSEResponse | JSONResponse:
    """Use AI to search the internet and summarize the result."""
    LOGGER.debug("user", user_id=user["id"])
    if input.stream:
        return SSEResponse(
            AI_SEARCH_SERVICE.ai_search_stream(user["id"], input.query),
        )
    else:
        output = await AI_SEARCH_SERVICE.ai_search(user["id"], input.query)
        return JSONResponse(output)
