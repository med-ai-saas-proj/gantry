from fastapi import APIRouter
from fastapi.params import Depends

from ..depends.auth import required_permission

router = APIRouter(prefix="/test")

@router.get("/")
async def test_endpoint(owner_id: str = Depends(required_permission(["test-permission-1"]))):
    return {"message": f"Test endpoint is working for user {owner_id} with test-permission-1"}

@router.get("/admin")
async def admin_endpoint(admin_id: str = Depends(required_permission(["admin-permission"]))):
    return {"message": f"Admin endpoint is working for admin {admin_id} with admin-permission"}