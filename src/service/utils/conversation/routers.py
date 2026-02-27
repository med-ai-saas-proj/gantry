from src.management.api_keys.entities import ApiKeyInfo
from src.management.api_keys.dependencies import requiredPermissions
from src.service.utils.conversation.services import ConversationService
from src.service.utils.conversation.factories import getConversationService

from .dtos import MessageResponse

import uuid
from typing import Sequence, Annotated

from fastapi import Depends, Security, APIRouter


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
    conversation_service: Annotated[ConversationService, Depends(getConversationService)]
):
    """Get conversation details and messages by conversation UID."""
    messages = (
        await conversation_service.getConversationMessageByUuid(
            conversation_uid,
            api_key_info["project_id"]
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