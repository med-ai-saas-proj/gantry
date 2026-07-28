from .tree_internal import tree_internal_router
from .sequence_internal import sequence_internal_router

from fastapi import APIRouter


conversation_internal_router = APIRouter(
    prefix="/conversations", tags=["conversation-internal"]
)
conversation_internal_router.include_router(
    sequence_internal_router, prefix="/sequence"
)
conversation_internal_router.include_router(
    tree_internal_router, prefix="/tree"
)
