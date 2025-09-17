from src.services.user import UserService
from src.services.postgres import PostgresService
from src.initialize.session_scopes import CORE_DB_SESSION_SCOPE

def get_user_service() -> UserService:
    session_scope = CORE_DB_SESSION_SCOPE
    postgres_service = PostgresService(session_scope)
    return UserService(postgres_service)