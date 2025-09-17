from typing import Annotated, Any, AsyncGenerator, TypedDict, NotRequired
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse

from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.logger import LOGGER
from src.utils.response import ResponseUtils
from src.initialize.services import RX_ADVISOR_SERVICE


router = APIRouter(tags=["Doctor Help"])


class SharedInput(TypedDict):
    ehr: dict[str, Any]
    prescription: dict[str, Any]
    stream: NotRequired[bool]


async def stream_summary(generator: AsyncGenerator[str, None]):
    async for delta in generator:
        data = {"d": delta}
        yield ResponseUtils.format_sse("delta", data)


@router.post("/rx_advisor")
async def rx_advisor(
    user: Annotated[User, Depends(get_current_user)], body: SharedInput
):
    LOGGER.debug("user", user_id=user["id"])
    if body.get("stream", False):
        return StreamingResponse(
            stream_summary(
                RX_ADVISOR_SERVICE.generate_advice_stream(
                    user["id"], body["ehr"], body["prescription"]
                )
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )
    else:
        analysis = await RX_ADVISOR_SERVICE.generate_advice(
            user["id"], body["ehr"], body["prescription"]
        )
        return JSONResponse({"analysis": analysis})
