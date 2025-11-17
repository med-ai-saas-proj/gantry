from sqlalchemy import text

from .services.api_keys import ApiKeyService, ApiKeyServiceConfig
from .services.users import UserService, UserServiceConfig
from src.db_v2.base import metadata
from src.db_v2.initialize import async_engine

user_service: UserService = None
api_key_service: ApiKeyService = None


async def init_auth_service(
    user_config: UserServiceConfig,
    api_key_config: ApiKeyServiceConfig,
    create_db_if_not_exists: bool = True,
):
    async def create_db():
        async with async_engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
            await conn.run_sync(metadata.create_all)

    if create_db_if_not_exists:
        await create_db()

    global user_service
    user_service = UserService(config=user_config)

    global api_key_service
    api_key_service = ApiKeyService(config=api_key_config)


def get_user_service() -> UserService:
    global user_service
    return user_service


def get_api_key_service() -> ApiKeyService:
    global api_key_service
    return api_key_service
