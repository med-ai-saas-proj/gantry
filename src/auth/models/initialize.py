from .users import UserRepo
from .api_keys import ApiKeyRepo, PermissionRepo


user_repo = UserRepo()
api_key_repo = ApiKeyRepo()
permission_repo = PermissionRepo()
