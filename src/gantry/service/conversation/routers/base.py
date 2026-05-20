from fastapi import APIRouter


conversation_router = APIRouter(
    prefix="/conversations",
    tags=["Conversation"],
)
