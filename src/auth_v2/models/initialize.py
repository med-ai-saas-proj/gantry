from .api_keys import ApiKeyRepo, PermissionRepo
from .users import UserRepo

user_repo = UserRepo()
api_key_repo = ApiKeyRepo()
permission_repo = PermissionRepo()