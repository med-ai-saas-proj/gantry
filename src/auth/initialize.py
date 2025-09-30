from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

from .services.user import UserService
from .services.api_key import ApiKeyServices


API_KEY_SERVICE = ApiKeyServices(CORE_DB_SESSION_SCOPE)
USER_SERVICE = UserService(CORE_DB_SESSION_SCOPE)