from src.auth.security import get_current_user
from src.auth.entities.user import User
from src.shared.utils.logger import LOGGER
from src.shared.custom_types.responses.sse import SSEResponse, SSEContent
from src.shared.dtos.generation_output import (
    ResponseStatus,
    Usage,
    GenerationOutput,
)

from .dtos import AiSearchInput, AiSearchOutput, Answer
from .initialize import AI_SEARCH_SERVICE

from typing import Annotated, AsyncGenerator, Any

from fastapi import Body, Security, APIRouter
from pydantic import TypeAdapter
from fastapi.responses import JSONResponse


ai_search_router = APIRouter(prefix="/ai_search", tags=["Doctor Help"])


@ai_search_router.post(
    "",
    response_model=AiSearchOutput,
    responses={
        200: {
            "content": {
                "stream/text-event": {},
                "application/json": {
                    "examples": {
                        "standard": {
                            "summary": "Typical item",
                            "value": AiSearchOutput(
                                id="resp_123",
                                conversation_id="conv_123",
                                status=ResponseStatus.completed,
                                output={
                                    "result": "This is the result",
                                    "reasoning": None,
                                    "viewed_pages": [],
                                    "citations": [],
                                },
                                usage={
                                    "input_tokens": 10,
                                    "output_tokens": 10,
                                },
                            ),
                        },
                    }
                },
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
            convert_stream(
                AI_SEARCH_SERVICE.generate_advice_stream(
                    user["id"], input.query
                ),
            )
        )
    else:
        analysis, usage = await AI_SEARCH_SERVICE.generate_advice(
            user["id"], input.query
        )
        return JSONResponse(
            AiSearchOutput(
                id="",
                conversation_id="",
                status=ResponseStatus.completed,
                output=analysis,
                usage=usage,
            )
        )


async def _convert_stream(stream: AsyncGenerator[Answer | Usage]):
    async for it in stream:
        if "input_tokens" in it:
            yield SSEContent(
                event=None,
                data=GenerationOutput[None](
                    id="",
                    conversation_id="",
                    status=ResponseStatus.completed,
                    output=None,
                    usage=it,
                ),
            )
        else:
            yield SSEContent(event="final_result", data=it)
