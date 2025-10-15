from src.auth.services.user import UserService
from src.auth.services.api_key import ApiKeyServices
from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

import asyncio


user_service = UserService(CORE_DB_SESSION_SCOPE)
api_key_service = ApiKeyServices(CORE_DB_SESSION_SCOPE)
email = "test@test.com"
password = "Thisisaverystrongpassword123"


async def main():
    try:
        user = await user_service.register_user(email=email, password=password)
        print(f"Created a test account with {email=}, {password=}")
    except:
        user = await user_service.get_user_by_email(email)
        print(f"Account already created {email=}, {password=}")
    api_key_service.
    api_key = await api_key_service.create_api_key(
        user["id"], "test frontent", expires_in_days=9999
    )
    print(f"Created an API key: {api_key=}")


if __name__ == "__main__":
    asyncio.run(main())
