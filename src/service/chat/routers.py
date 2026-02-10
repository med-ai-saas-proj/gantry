"""This file contain definition of chat's routers."""

from src.shared.utils.logger import LOGGER
from src.management.auth.dependencies import UserInfo, getUserInfo
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
    LOGGER.debug("api_key_info", api_key_info=api_key_info)

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


conversation_router = APIRouter(prefix="/conversation")


@conversation_router.post("")
def create_conversation(
    user: Annotated[UserInfo, Security(getUserInfo)],
    input,
):
    return {"id": "conv-123981"}


@conversation_router.get("/{conversation_id}")
def get_conversation(
    user: Annotated[UserInfo, Security(getUserInfo)], conversation_id: str
):
    return {
        "id": "conv-1231",
        "created_at": "",
        "updated_at": "",
        "metadata": {},
    }


@conversation_router.put("/{conversation_id}")
def replace_conversation_metadata(
    user: Annotated[UserInfo, Security(getUserInfo)],
    conversation_id: str,
    metadata: Annotated[dict[str, str], Body(embed=True)],
):
    pass


@conversation_router.patch("/{conversation_id}")
def merge_conversation_metadata(
    user: Annotated[UserInfo, Security(getUserInfo)],
    conversation_id: str,
    new_metadata: Annotated[dict[str, str | None], Body(embed=True)],
):
    # if value is none then delete the key
    pass


@conversation_router.get("/{conversation_id}/messages")
def get_messages(
    user: Annotated[UserInfo, Security(getUserInfo)],
    conversation_id: str,
    limit,
    order,
):
    return {
        "id": "conv-1231",
        "created_at": "",
        "updated_at": "",
        "metadata": {},
    }


@conversation_router.get(path="/attatchment/{attachment_id}")
def get_attachment(
    user: Annotated[UserInfo, Security(getUserInfo)], attatchment_id: str
):
    pass
