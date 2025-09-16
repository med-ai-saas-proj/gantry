from typing import Annotated, AsyncGenerator
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse, Response
import starlette.status as HTTP_Status
from xml.etree import ElementTree
import json

from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.logger import LOGGER
from src.utils.dict_utils import DictUtils
from src.initialize.services import EHR_SUMMARY_SERVICE
from src.custom_types.responses import CErrorResponse

router = APIRouter()


async def extract_ehr(request: Request):
    try:
        body = (await request.body()).decode()
        # LOGGER.debug("XML", body)
        parsed_xml = ElementTree.fromstring(body)
        body_dict = DictUtils.xml_to_dict(parsed_xml)
        if not body_dict:
            raise
        # LOGGER.debug("Converted XML", body_dict)
        return body_dict
    except Exception as e:
        LOGGER.debug("Error parsing XML", e)
        return CErrorResponse(
            HTTP_Status.HTTP_400_BAD_REQUEST,
            HTTP_Status.HTTP_400_BAD_REQUEST,
            "EHR not found or malformed",
        )


@router.post("/ehr_summarize")
async def summarize_ehr(
    user: Annotated[User, Depends(get_current_user)],
    ehr: Annotated[dict, Depends(extract_ehr)],
):
    LOGGER.debug("user", user_id=user["id"])
    summary = await EHR_SUMMARY_SERVICE.summarize_ehr(user["id"], ehr)
    return JSONResponse({"summary": summary})


async def stream_summary(generator: AsyncGenerator[str]):
    async for delta in generator:
        data = {"d": delta}
        yield f"event: delta\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/ehr_summarize_stream")
async def summarize_ehr_stream(
    user: Annotated[User, Depends(get_current_user)],
    ehr: Annotated[dict, Depends(extract_ehr)],
):
    LOGGER.debug("user", user_id=user["id"])
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
