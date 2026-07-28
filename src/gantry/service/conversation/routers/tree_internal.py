from gantry.shared.dependencies import getProjectId

from ..dtos import (
    Message,
    AddTreeMessageRequest,
    CreateConversationRequest,
    GetMessagesByUuidsRequest,
    CreateConversationResponse,
    ConversationMetadataResponse,
    UpdateConversationMetadataRequest,
)
from ..factories import (
    getTreeConversationService,
    getSequenceConversationService,
)
from ..services.tree import TreeConversationService
from ..services.sequence import SequenceConversationService

import uuid
from typing import Literal, Sequence, Annotated

from fastapi import Body, Query, Depends, APIRouter


tree_internal_router = APIRouter()


@tree_internal_router.post(
    "/",
    summary="Create a new tree conversation (internal)",
    description="Endpoint to create a new tree conversation.",
    response_model=CreateConversationResponse,
    status_code=201,
)
async def create_tree_conversation(
    body: Annotated[CreateConversationRequest, Body()],
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        TreeConversationService, Depends(getTreeConversationService)
    ],
):
    conversation_uid = (
        await conversation_service.createConversation(
            project_id=project_id,
            extra_metadata=body.extra_metadata,
            messages=body.messages,
        )
    ).unwrap()
    return CreateConversationResponse(conversation_uid=conversation_uid)


@tree_internal_router.get(
    "/{conversation_uid}",
    summary="Get tree conversation metadata (internal)",
    description="Endpoint to retrieve tree conversation details by conversation UID.",
    response_model=ConversationMetadataResponse,
)
async def get_tree_conversation_metadata(
    conversation_uid: uuid.UUID,
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        SequenceConversationService, Depends(getSequenceConversationService)
    ],
):
    metadata = (
        await conversation_service.getConversationMetadata(
            conversation_uid, project_id
        )
    ).unwrap()
    return ConversationMetadataResponse(
        conversation_uid=metadata["conversation_uid"],
        project_id=metadata["project_id"],
        extra_metadata=metadata["extra_metadata"],
        created_at=metadata["created_at"],
        tree_structure=metadata.get("tree_structure"),
        active_leaf_message_id=metadata.get("active_leaf_message_id"),
        conversation_type=metadata.get("conversation_type"),
        relationships_map=metadata.get("relationships_map"),
    )


@tree_internal_router.put(
    "/{conversation_uid}/metadata",
    summary="Update tree conversation metadata (internal)",
    description="Endpoint to update tree conversation metadata by conversation UID.",
    status_code=204,
)
async def update_tree_conversation_metadata(
    conversation_uid: uuid.UUID,
    body: Annotated[UpdateConversationMetadataRequest, Body()],
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        TreeConversationService, Depends(getTreeConversationService)
    ],
):
    (
        await conversation_service.updateConversationMetadata(
            conversation_uid=conversation_uid,
            project_id=project_id,
            extra_metadata=body.extra_metadata,
        )
    ).unwrap()


@tree_internal_router.delete(
    "/{conversation_uid}",
    summary="Delete a tree conversation (internal)",
    description="Endpoint to delete a tree conversation by conversation UID.",
    status_code=204,
)
async def delete_tree_conversation(
    conversation_uid: uuid.UUID,
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        TreeConversationService, Depends(getTreeConversationService)
    ],
):
    (
        await conversation_service.deleteConversation(
            conversation_uid, project_id
        )
    ).unwrap()


@tree_internal_router.get(
    "/{conversation_uid}/messages",
    summary="Get tree conversation messages (internal)",
    description="Endpoint to retrieve tree conversation details and messages by conversation UID.",
    response_model=Sequence[Message],
)
async def get_tree_conversation_messages(
    conversation_uid: uuid.UUID,
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        TreeConversationService, Depends(getTreeConversationService)
    ],
    last_cursor: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(gt=0, le=100)] = 20,
    order_by: Annotated[Literal["asc", "desc"], Query()] = "asc",
    branch_message_uid: Annotated[uuid.UUID | None, Query()] = None,
):
    messages = (
        await conversation_service.getConversationMessages(
            conversation_uid,
            project_id,
            limit=limit,
            last_cursor=last_cursor,
            order_by=order_by,
            branch_node_id=branch_message_uid,
        )
    ).unwrap()
    res: list[Message] = []

    for mess in messages:
        res.append(
            Message(
                message_uid=mess.uuid,
                payload=mess.payload,
                run_id=mess.run_id,
                timestamp=mess.timestamp,
                extra_metadata=mess.extra_metadata,
            )
        )
    return res


@tree_internal_router.post(
    "/{conversation_uid}/messages",
    summary="Add a message to the tree conversation (internal)",
    description="Endpoint to add a new message to the tree conversation by conversation UID.",
    status_code=201,
)
async def add_tree_message_to_conversation(
    conversation_uid: uuid.UUID,
    body: Annotated[AddTreeMessageRequest, Body()],
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        TreeConversationService, Depends(getTreeConversationService)
    ],
):
    (
        await conversation_service.storeConversationMessages(
            conversation_uid=conversation_uid,
            project_id=project_id,
            msgs=body.messages,
            from_node_id=body.from_message_uid,
        )
    ).unwrap()


@tree_internal_router.delete(
    "/{conversation_uid}/messages/{message_uid}",
    summary="Delete a message from the tree conversation (internal)",
    description="Endpoint to delete a message from the tree conversation by conversation UID and message UID.",
    status_code=204,
)
async def delete_tree_message_from_conversation(
    conversation_uid: uuid.UUID,
    message_uid: uuid.UUID,
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        TreeConversationService, Depends(getTreeConversationService)
    ],
):
    (
        await conversation_service.deleteConversationMessage(
            conversation_uid=conversation_uid,
            project_id=project_id,
            message_uid=message_uid,
        )
    ).unwrap()


@tree_internal_router.post(
    "/{conversation_uid}/messages/bulk",
    summary="Get multiple messages by UIDs from the tree conversation (internal)",
    description="Endpoint to retrieve multiple specific messages from the tree conversation by conversation UID and message UIDs.",
    response_model=Sequence[Message],
)
async def get_tree_messages_from_conversation(
    conversation_uid: uuid.UUID,
    body: Annotated[GetMessagesByUuidsRequest, Body()],
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        TreeConversationService, Depends(getTreeConversationService)
    ],
):
    res = await conversation_service.getConversationMessagesByUuids(
        conversation_uid=conversation_uid,
        project_id=project_id,
        message_uids=body.message_uids,
    )
    return [
        Message(
            message_uid=msg.uuid,
            payload=msg.payload,
            run_id=msg.run_id,
            timestamp=msg.timestamp,
            extra_metadata=msg.extra_metadata,
        )
        for msg in res
    ]


@tree_internal_router.get(
    "/{conversation_uid}/messages/{message_uid}",
    summary="Get a specific message from the tree conversation (internal)",
    description="Endpoint to retrieve a specific message from the tree conversation by conversation UID and message UID.",
    response_model=Message,
)
async def get_tree_message_from_conversation(
    conversation_uid: uuid.UUID,
    message_uid: uuid.UUID,
    project_id: Annotated[int, Depends(getProjectId)],
    conversation_service: Annotated[
        TreeConversationService, Depends(getTreeConversationService)
    ],
):
    res = (
        await conversation_service.getConversationMessageByUuid(
            conversation_uid=conversation_uid,
            project_id=project_id,
            message_uid=message_uid,
        )
    ).unwrap()
    return Message(
        message_uid=res.uuid,
        payload=res.payload,
        run_id=res.run_id,
        timestamp=res.timestamp,
        extra_metadata=res.extra_metadata,
    )
