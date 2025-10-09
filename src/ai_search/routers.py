from src.auth.security import get_current_user
from src.auth.entities.user import User
from src.shared.utils.logger import LOGGER
from src.shared.custom_types.responses import SSEResponse
from src.shared.dtos.generation_output import ResponseStatus

from .dtos import AiSearchInput, AiSearchOutput
from .initialize import AI_SEARCH_SERVICE

from typing import Annotated

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
                                    "references": [],
                                    "citation": [],
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
    LOGGER.debug("user", user_id=user["id"])
    if input.stream:
        return SSEResponse(
            AI_SEARCH_SERVICE.generate_advice_stream(user["id"], input.query),
        )
    else:
        analysis = await AI_SEARCH_SERVICE.generate_advice(
            user["id"], input.query
        )
        return JSONResponse(
            AiSearchOutput(
                id="",
                conversation_id="",
                status=ResponseStatus.completed,
                output=analysis,
                usage={"input_tokens": 0, "output_tokens": 0},
            )
        )
