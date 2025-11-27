from .users import UserRepository
from .api_keys import ApiKeyRepository, PermissionRepository


user_repo = UserRepository()
api_key_repo = ApiKeyRepository()
permission_repo = PermissionRepository()
