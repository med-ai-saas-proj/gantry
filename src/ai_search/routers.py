from src.auth.security import get_current_user
from src.auth.entities.user import User
from src.shared.utils.logger import LOGGER
from src.shared.custom_types.responses import SSEResponse

from .services import Answer
from .initialize import AI_SEARCH_SERVICE

from typing import Annotated

from fastapi import Body, Security, APIRouter
from fastapi.responses import JSONResponse


ai_search_router = APIRouter(prefix="/ai_search", tags=["Doctor Help"])


@ai_search_router.post(
    "",
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
