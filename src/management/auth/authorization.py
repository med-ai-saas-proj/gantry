"""Authorization decorators and dependencies for role-based access control."""

from src.shared.consts import messages_const
from src.shared.custom_types.error_exception import RecoverableError

from .entities import UserInfo
from .roles import ManagementRole, has_role, has_any_role, has_all_roles

from typing import Callable
from functools import wraps

from fastapi import HTTPException, status


class ForbiddenError(RecoverableError):
    """Raised when user doesn't have required permissions."""
    
    status = 403
    code = "forbidden"
    title = "Forbidden"
    detail = "You don't have permission to perform this action."


class InsufficientPermissionsError(ForbiddenError):
    """Raised when user lacks specific role permissions."""
    
    def __init__(self, required_roles: list[str]):
        super().__init__()
        roles_str = ", ".join(required_roles)
        self.detail = (
            f"Insufficient permissions. Required roles: {roles_str}"
        )


def require_role(role: ManagementRole):
    """Decorator to require a specific role for an endpoint.
    
    Usage:
        @router.post("/members")
        @require_role(ManagementRole.MEMBER_ADD)
        async def create_member(user_info: UserInfo = Depends(getUserInfo)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_info from kwargs
            user_info: UserInfo | None = kwargs.get('user_info')
            
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            if not has_role(user_info.get('roles'), role):
                raise InsufficientPermissionsError([role.value])
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_any_role(*roles: ManagementRole):
    """Decorator to require any of the specified roles.
    
    Usage:
        @router.get("/members")
        @require_any_role(ManagementRole.MEMBER_VIEW, ManagementRole.MEMBER_ADMIN)
        async def list_members(user_info: UserInfo = Depends(getUserInfo)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_info: UserInfo | None = kwargs.get('user_info')
            
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            if not has_any_role(user_info.get('roles'), list(roles)):
                role_values = [r.value for r in roles]
                raise InsufficientPermissionsError(role_values)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_all_roles(*roles: ManagementRole):
    """Decorator to require all of the specified roles.
    
    Usage:
        @router.post("/admin/critical")
        @require_all_roles(ManagementRole.SUPER_ADMIN, ManagementRole.AUDIT_VIEW)
        async def critical_operation(user_info: UserInfo = Depends(getUserInfo)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_info: UserInfo | None = kwargs.get('user_info')
            
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            if not has_all_roles(user_info.get('roles'), list(roles)):
                role_values = [r.value for r in roles]
                raise InsufficientPermissionsError(role_values)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_role(user_info: UserInfo, role: ManagementRole) -> None:
    """Check if user has a specific role, raise exception if not.
    
    Usage:
        def some_service_method(self, user_info: UserInfo):
            check_role(user_info, ManagementRole.MEMBER_EDIT)
            # Continue with operation
    """
    if not has_role(user_info.get('roles'), role):
        raise InsufficientPermissionsError([role.value])


def check_any_role(user_info: UserInfo, *roles: ManagementRole) -> None:
    """Check if user has any of the specified roles, raise exception if not."""
    if not has_any_role(user_info.get('roles'), list(roles)):
        role_values = [r.value for r in roles]
        raise InsufficientPermissionsError(role_values)


def check_all_roles(user_info: UserInfo, *roles: ManagementRole) -> None:
    """Check if user has all of the specified roles, raise exception if not."""
    if not has_all_roles(user_info.get('roles'), list(roles)):
        role_values = [r.value for r in roles]
        raise InsufficientPermissionsError(role_values)
