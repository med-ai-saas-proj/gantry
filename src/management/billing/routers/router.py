from fastapi import APIRouter


billing_router = APIRouter(
    prefix="/billing",
    tags=["billing"],
)
