from src.management.api_keys.entities import ApiKeyInfo
from src.management.api_keys.dependencies import requiredPermissions
from src.service.utils.conversation.services import ConversationService
from src.service.utils.conversation.factories import getConversationService

from .dtos import MessageResponse

import uuid
from typing import Literal, Sequence, Annotated

from fastapi import Query, Depends, Security, APIRouter


conversation_router = APIRouter(
    prefix="/conversations",
    tags=["Conversation"],
)

@conversation_router.get(
    "/{conversation_uid}",
    summary="Get conversation messages",
    description="Endpoint to retrieve conversation details and messages by conversation UID.",
    response_model=Sequence[MessageResponse],
)
async def get_conversation(
    conversation_uid: uuid.UUID,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    conversation_service: Annotated[ConversationService, Depends(getConversationService)],
    last_cursor: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query( gt=0, le=100)] = 20,
    order_by: Annotated[Literal["asc", "desc"], Query()] = "asc",
):
    """Get conversation details and messages by conversation UID."""
    messages = (
        await conversation_service.getConversationMessageByUuid(
            conversation_uid,
            api_key_info["project_id"],
            limit=limit,
            last_cursor=last_cursor,
            order_by=order_by,
        )
    ).unwrap()
    return [MessageResponse.from_orm(mess) for mess in messages]


@conversation_router.post(
    "/{conversation_uid}",
    summary="Add a message to the conversation, creating a new conversation if the UID does not exist.",
    description="Endpoint to add a new message to the conversation by conversation UID.",
)
async def add_message_to_conversation(
    conversation_uid: uuid.UUID,
):
    pass