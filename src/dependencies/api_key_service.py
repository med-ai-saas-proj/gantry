from src.services.api_key_services import ApiKeyServices
from src.services.postgres import PostgresService
from src.initialize.session_scopes import CORE_DB_SESSION_SCOPE

def get_api_key_service() -> ApiKeyServices:
    session_scope = CORE_DB_SESSION_SCOPE
    postgres_service = PostgresService(session_scope)
    return ApiKeyServices(postgres_service)