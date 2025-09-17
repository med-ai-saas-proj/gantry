from typing import Annotated, Any, AsyncGenerator, TypedDict, NotRequired
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse

from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.logger import LOGGER
from src.utils.response import ResponseUtils
from src.initialize.services import EHR_SUMMARY_SERVICE


router = APIRouter()


class SharedInput(TypedDict):
    ehr: dict[str, Any]
    stream: NotRequired[bool]


async def stream_summary(generator: AsyncGenerator[str, None]):
    async for delta in generator:
        data = {"d": delta}
        yield ResponseUtils.format_sse("delta", data)


@router.post("/ehr_summarize")
async def summarize_ehr(
    user: Annotated[User, Depends(get_current_user)], body: SharedInput
):
    LOGGER.debug("user", user_id=user["id"])
    if body.get("stream", False):
        return StreamingResponse(
            stream_summary(
                EHR_SUMMARY_SERVICE.summarize_ehr_stream(
                    user["id"], body["ehr"]
                )
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )
    else:
        summary = await EHR_SUMMARY_SERVICE.summarize_ehr(
            user["id"], body["ehr"]
        )
        return JSONResponse({"summary": summary})
