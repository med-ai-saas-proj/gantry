from gantry.service.rag.services import RagService
from gantry.service.rag.factories import getRagService

from typing import Sequence, Annotated

from fastapi import Depends, APIRouter


rag_router = APIRouter(prefix="/rag", tags=["rag"])


@rag_router.get(
    "/supported-languages", summary="Get supported languages for BM25 search."
)
def get_supported_languages(
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> Sequence[str]:
    """Get the list of supported languages for BM25 search."""
    return rag_service.getSupportedLanguages()
