from .auth import auth_router as auth_router_
from .api_key import api_key_router

from fastapi import APIRouter


auth_router = APIRouter()
auth_router.include_router(auth_router_)
auth_router.include_router(api_key_router)
