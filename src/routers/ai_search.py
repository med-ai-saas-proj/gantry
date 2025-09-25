from typing import Annotated
from fastapi import APIRouter, Security, Body
from fastapi.responses import JSONResponse

from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.logger import LOGGER
from src.initialize.services import AI_SEARCH_SERVICE
from src.services.ai_search import Answer
from src.custom_types.responses import SSEResponse


router = APIRouter(tags=["Doctor Help"])


@router.post(
    "/ai_search",
    response_model=Answer,
    responses={
        200: {
            "content": {
                "stream/text-event": {},
            },
        }
    },
)
async def ai_search(
    user: Annotated[User, Security(get_current_user)],
    query: str = Body(..., embed=True),
    stream: bool = Body(False, embed=True),
):
    LOGGER.debug("user", user_id=user["id"])
    if stream:
        return SSEResponse(
            AI_SEARCH_SERVICE.generate_advice_stream(user["id"], query),
        )
    else:
        analysis = await AI_SEARCH_SERVICE.generate_advice(user["id"], query)
        return JSONResponse(analysis)
