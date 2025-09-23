from typing import (
    Annotated,
    AsyncGenerator,
    TypedDict,
    NotRequired,
)
from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse, JSONResponse

from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.logger import LOGGER
from src.utils.response import ResponseUtils
from src.initialize.services import EHR_SUMMARY_SERVICE
from src.dtos.ehr import InputEHR
from src.custom_types.ehr import EHRDict


router = APIRouter(tags=["Doctor Help"])


class SharedInput(TypedDict):
    ehr: InputEHR
    stream: NotRequired[bool]


async def stream_summary(generator: AsyncGenerator[str, None]):
    async for delta in generator:
        data = {"d": delta}
        yield ResponseUtils.format_sse("delta", data)


@router.post("/ehr_summarize")
async def summarize_ehr(
    user: Annotated[User, Depends(get_current_user)],
    ehr: InputEHR,
    stream: bool = Body(False, embed=True),
):
    LOGGER.debug("user", user_id=user["id"])
    if stream:
        return StreamingResponse(
            stream_summary(
                EHR_SUMMARY_SERVICE.summarize_ehr_stream(user["id"], ehr)
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )
    else:
        summary = await EHR_SUMMARY_SERVICE.summarize_ehr(user["id"], ehr)
        return JSONResponse({"summary": summary})
