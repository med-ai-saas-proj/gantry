from fastapi import APIRouter


internal_billing_router = APIRouter(
    prefix="/billing",
    tags=["billing", "internal"],
)
