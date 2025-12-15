"""This file contain definition of chat's routers."""

from src.shared.utils.logger import LOGGER
from src.management.auth.dependencies import UserInfo, getUserInfo
from src.shared.custom_types.responses.sse import SSEResponse

from .dtos import ChatInput, ChatOutput
from .factories import ChatService, getChatService

from typing import Annotated

from fastapi import Body, Depends, Security, APIRouter
from fastapi.responses import JSONResponse


model_router = APIRouter(prefix="/models")


@model_router.get(path="")
def get_all_model(user: Annotated[UserInfo, Security(getUserInfo)], input):
    pass


@model_router.get(path="/{model_name}")
def get_model(
    user: Annotated[UserInfo, Security(getUserInfo)], model_name: str
):
    pass


@model_router.post(path="")
def create_model(user: Annotated[UserInfo, Security(getUserInfo)], input):
    pass


@model_router.put(path="{model_name}")
def update_model(
    user: Annotated[UserInfo, Security(getUserInfo)], model_name: str
):
    pass


@model_router.delete(path="/{model_name}")
def delete_model(
    user: Annotated[UserInfo, Security(getUserInfo)], model_name: str
):
    pass


chat_router = APIRouter(prefix="/chat")


@chat_router.post("", response_model=ChatOutput)
async def chat(
    user: Annotated[UserInfo, Security(getUserInfo)],
    input: Annotated[ChatInput, Body()],
):
    """Just the good old chatbot."""
    LOGGER.debug("user", user_id=user_id)
    if input.stream:
        return SSEResponse(
            chat_service.chat_stream(user_id, input.input),
        )
    else:
        output = await chat_service.chat(user_id, input.input)
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
