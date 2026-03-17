"""This file contain definition of chat's routers."""

from src.shared.logging.logger import LOGGER, getServiceLogger
from src.shared.custom_types.responses.sse import SSEResponse

from .dtos import ChatInput
from .factories import ChatService, getChatService
from ..utils.agent.dtos.model import ChatOutput, StreamEvent
from ...management.api_keys.entities import ApiKeyInfo
from ...management.api_keys.dependencies import requiredPermissions

from typing import Annotated

from fastapi import Body, Depends, Security, APIRouter
from fastapi.responses import JSONResponse


chat_router = APIRouter(prefix="/chat")


@chat_router.post("", response_model=ChatOutput | StreamEvent)
async def chat(
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    input: Annotated[ChatInput, Body()],
    chat_service: Annotated[ChatService, Depends(getChatService)],
):
    """Just the good old chatbot."""
    getServiceLogger(
        "Med-AI-SaaS", api_key_info["project_uid"], api_key_info["org_id"]
    ).debug("api_key_info", api_key_info=api_key_info)

    if input.stream:
        return SSEResponse(
            chat_service.chatStream(
                api_key_info, input.model, input.input, input.conversation_id
            ),
        )
    else:
        output = await chat_service.chat(
            api_key_info, input.model, input.input, input.conversation_id
        )
        return JSONResponse(output)
