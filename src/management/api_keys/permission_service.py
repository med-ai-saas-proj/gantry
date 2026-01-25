"""Service for managing permissions."""

from src.db.factories import AsyncSessionManager
from src.shared.custom_types.error_exception import RecoverableError

from .permission_dtos import (
    PermissionOutput,
    PermissionListOutput,
)
from .repositories import PermissionRepository

from safe_result import Ok, Err, Result
from structlog.stdlib import BoundLogger


class PermissionAlreadyExistsError(RecoverableError):
    """Raised when a permission with the same name already exists."""

    status = 409
    code = "permission_already_exists"
    title = "Permission Already Exists"
    detail = "A permission with this name already exists."


class PermissionNotFoundError(RecoverableError):
    """Raised when a permission is not found."""

    status = 404
    code = "permission_not_found"
    title = "Permission Not Found"
    detail = "The requested permission does not exist."


class PermissionInUseError(RecoverableError):
    """Raised when trying to delete a permission that is in use."""

    status = 409
    code = "permission_in_use"
    title = "Permission In Use"
    detail = (
        "Cannot delete permission as it is currently "
        "assigned to one or more API keys."
    )


class PermissionService:
    """Service for managing permissions."""

    def __init__(
        self,
        logger: BoundLogger,
        permission_repo: PermissionRepository,
        session_manager: AsyncSessionManager,
    ):
        """Initialize the PermissionService."""
        self.logger = logger
        self.permission_repo = permission_repo
        self.session_manager = session_manager

    async def createPermission(
        self, name: str, description: str
    ) -> Result[PermissionOutput, PermissionAlreadyExistsError]:
        """Create a new permission."""
        async with self.session_manager.get_session() as session:
            # Check if permission already exists
            existing = await self.permission_repo.getPermissionByName(
                session, name
            )
            if existing:
                return Err(PermissionAlreadyExistsError())

            # Create the permission
            permission = await self.permission_repo.createPermission(
                session, name, description
            )

            # Access attributes before commit to avoid detached instance
            permission_data = PermissionOutput(
                id=permission.id,
                name=permission.name,
                description=permission.description,
                created_at=permission.created_at,
                updated_at=permission.updated_at,
            )

            await session.commit()

            return Ok(permission_data)

    async def getPermissions(
        self, skip: int = 0, limit: int = 100
    ) -> Result[PermissionListOutput, None]:
        """Get all permissions with pagination."""
        async with self.session_manager.get_session() as session:
            permissions = await self.permission_repo.getAllPermissions(
                session, skip, limit
            )
            total = await self.permission_repo.countPermissions(session)

            return Ok(
                PermissionListOutput(
                    permissions=[
                        PermissionOutput(
                            id=p.id,
                            name=p.name,
                            description=p.description,
                            created_at=p.created_at,
                            updated_at=p.updated_at,
                        )
                        for p in permissions
                    ],
                    total=total,
                )
            )

    async def getPermissionById(
        self, permission_id: int
    ) -> Result[PermissionOutput, PermissionNotFoundError]:
        """Get a permission by ID."""
        async with self.session_manager.get_session() as session:
            permission = await self.permission_repo.getPermissionById(
                session, permission_id
            )
            if not permission:
                return Err(PermissionNotFoundError())

            return Ok(
                PermissionOutput(
                    id=permission.id,
                    name=permission.name,
                    description=permission.description,
                    created_at=permission.created_at,
                    updated_at=permission.updated_at,
                )
            )

    async def updatePermission(
        self, permission_id: int, description: str
    ) -> Result[PermissionOutput, PermissionNotFoundError]:
        """Update a permission's description."""
        async with self.session_manager.get_session() as session:
            permission = await self.permission_repo.getPermissionById(
                session, permission_id
            )
            if not permission:
                return Err(PermissionNotFoundError())

            updated = await self.permission_repo.updatePermission(
                session, permission, description
            )

            # Access attributes before commit to avoid detached instance
            permission_data = PermissionOutput(
                id=updated.id,
                name=updated.name,
                description=updated.description,
                created_at=updated.created_at,
                updated_at=updated.updated_at,
            )

            await session.commit()

            return Ok(permission_data)

    async def deletePermission(
        self, permission_id: int
    ) -> Result[bool, PermissionNotFoundError | PermissionInUseError]:
        """Delete a permission if it's not in use."""
        async with self.session_manager.get_session() as session:
            permission = await self.permission_repo.getPermissionById(
                session, permission_id
            )
            if not permission:
                return Err(PermissionNotFoundError())

            # Check if permission is in use by any API keys
            from sqlalchemy import select, exists
            from .models import ApiKeyPermission

            stmt = select(
                exists().where(
                    ApiKeyPermission.permission_id == permission_id
                )
            )
            result = await session.execute(stmt)
            is_in_use = result.scalar()

            if is_in_use:
                return Err(PermissionInUseError())

            await self.permission_repo.deletePermission(session, permission)
            await session.commit()

            return Ok(True)
