from gantry.management.api_key import ApiKeyInfo, requiredPermissions

from ..dtos import (
    AddMessageRequest,
    RequestMessagePart,
    ResponseMessagePart,
    RequestMessageResponse,
    ResponseMessageResponse,
    CreateConversationRequest,
    CreateConversationResponse,
    ConversationMetadataResponse,
    UpdateConversationMetadataRequest,
)
from ..factories import getSequenceConversationService
from ..services.sequence import SequenceConversationService

import uuid
from typing import Literal, Sequence, Annotated, cast

from fastapi import Body, Query, Depends, Security, APIRouter


conversation_router = APIRouter(
    prefix="/conversations/sequence",
    tags=["Conversation"],
)


@conversation_router.post(
    "/",
    summary="Create a new conversation",
    description="Endpoint to create a new conversation.",
    response_model=CreateConversationResponse,
    status_code=201,
)
async def create_conversation(
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["conversation.write"]))
    ],
    body: Annotated[CreateConversationRequest, Body()],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
):
    """Create a new conversation."""
    conversation_uid = await conversation_service.createConversation(
        project_id=api_key_info["project_id"],
        extra_metadata=body.extra_metadata,
        messages=body.messages,
    )
    return CreateConversationResponse(conversation_uid=conversation_uid)


@conversation_router.get(
    "/{conversation_uid}",
    summary="Get conversation metadata",
    description="Endpoint to retrieve conversation details by conversation UID.",
    response_model=ConversationMetadataResponse,
)
async def get_conversation_metadata(
    conversation_uid: uuid.UUID,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["conversation.read"]))
    ],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
):
    """Get conversation metadata by conversation UID."""
    metadata = (
        await conversation_service.getConversationMetadata(
            conversation_uid, api_key_info["project_id"]
        )
    ).unwrap()
    return ConversationMetadataResponse(
        conversation_uid=metadata["conversation_uid"],
        project_id=metadata["project_id"],
        extra_metadata=metadata["extra_metadata"],
        created_at=metadata["created_at"],
    )


@conversation_router.put(
    "/{conversation_uid}/metadata",
    summary="Update conversation metadata",
    description="Endpoint to update conversation metadata by conversation UID.",
    status_code=204,
)
async def update_conversation_metadata(
    conversation_uid: uuid.UUID,
    body: Annotated[UpdateConversationMetadataRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["conversation.write"]))
    ],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
):
    """Update conversation metadata by conversation UID."""
    (
        await conversation_service.updateConversationMetadata(
            conversation_uid=conversation_uid,
            project_id=api_key_info["project_id"],
            extra_metadata=body.extra_metadata,
        )
    ).unwrap()


@conversation_router.delete(
    "/{conversation_uid}",
    summary="Delete a conversation",
    description="Endpoint to delete a conversation by conversation UID.",
    status_code=204,
)
async def delete_conversation(
    conversation_uid: uuid.UUID,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["conversation.delete"]))
    ],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
):
    """Delete a conversation by conversation UID."""
    (
        await conversation_service.deleteConversation(
            conversation_uid, api_key_info["project_id"]
        )
    ).unwrap()


@conversation_router.get(
    "/{conversation_uid}/messages",
    summary="Get conversation messages",
    description="Endpoint to retrieve conversation details and messages by conversation UID.",
    response_model=Sequence[ResponseMessageResponse | RequestMessageResponse],
)
async def get_conversation_messages(
    conversation_uid: uuid.UUID,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["conversation.read"]))
    ],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
    last_cursor: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(gt=0, le=100)] = 20,
    order_by: Annotated[Literal["asc", "desc"], Query()] = "asc",
):
    """Get conversation details and messages by conversation UID."""
    messages = (
        await conversation_service.getConversationMessages(
            conversation_uid,
            api_key_info["project_id"],
            limit=limit,
            last_cursor=last_cursor,
            order_by=order_by,
        )
    ).unwrap()
    res: list[ResponseMessageResponse | RequestMessageResponse] = []

    for mess in messages:
        if mess.kind == "request":
            res.append(
                RequestMessageResponse(
                    message_uid=mess.uuid,
                    kind="request",
                    parts=cast(list[RequestMessagePart], mess.parts),
                    model_name=mess.model_name,
                    timestamp=mess.timestamp,
                    run_id=mess.run_id,
                )
            )
        elif mess.kind == "response":
            res.append(
                ResponseMessageResponse(
                    message_uid=mess.uuid,
                    kind="response",
                    parts=cast(list[ResponseMessagePart], mess.parts),
                    model_name=mess.model_name,
                    timestamp=mess.timestamp,
                    run_id=mess.run_id,
                )
            )
    return res


@conversation_router.post(
    "/{conversation_uid}/messages",
    summary="Add a message to the conversation.",
    description="Endpoint to add a new message to the conversation by conversation UID.",
    status_code=201,
)
async def add_message_to_conversation(
    conversation_uid: uuid.UUID,
    body: Annotated[AddMessageRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["conversation.write"]))
    ],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
):
    (
        await conversation_service.storeConversationMessages(
            conversation_uid=conversation_uid,
            project_id=api_key_info["project_id"],
            msgs=body.messages,
        )
    ).unwrap()


@conversation_router.delete(
    "/{conversation_uid}/messages/{message_uid}",
    summary="Delete a message from the conversation.",
    description="Endpoint to delete a message from the conversation by conversation UID and message UID.",
    status_code=204,
)
async def delete_message_from_conversation(
    conversation_uid: uuid.UUID,
    message_uid: uuid.UUID,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["conversation.write"]))
    ],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
):
    """Delete a message from the conversation by conversation UID and message UID."""
    (
        await conversation_service.deleteConversationMessage(
            conversation_uid=conversation_uid,
            project_id=api_key_info["project_id"],
            message_uid=message_uid,
        )
    ).unwrap()


@conversation_router.get(
    "/{conversation_uid}/messages/{message_uid}",
    summary="Get a specific message from the conversation.",
    description="Endpoint to retrieve a specific message from the conversation by conversation UID and message UID.",
    response_model=ResponseMessageResponse | RequestMessageResponse,
)
async def get_message_from_conversation(
    conversation_uid: uuid.UUID,
    message_uid: uuid.UUID,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["conversation.read"]))
    ],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
):
    res = (
        await conversation_service.getConversationMessageByUuid(
            conversation_uid=conversation_uid,
            project_id=api_key_info["project_id"],
            message_uid=message_uid,
        )
    ).unwrap()
    if res.kind == "request":
        return RequestMessageResponse(
            message_uid=res.uuid,
            kind="request",
            parts=cast(list[RequestMessagePart], res.parts),
            model_name=res.model_name,
            timestamp=res.timestamp,
            run_id=res.run_id,
        )
    elif res.kind == "response":
        return ResponseMessageResponse(
            message_uid=res.uuid,
            kind="response",
            parts=cast(list[ResponseMessagePart], res.parts),
            model_name=res.model_name,
            timestamp=res.timestamp,
            run_id=res.run_id,
        )
