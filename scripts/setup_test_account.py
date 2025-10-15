from src.auth.services.user import UserService
from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

import asyncio


user_service = UserService(CORE_DB_SESSION_SCOPE)
email = "test@test.com"
password = "Thisisaverystrongpassword123"


async def main():
    await user_service.register_user(email=email, password=password)
    print(f"Created a test account with {email=}, {password=}")


if __name__ == "__main__":
    asyncio.run(main())
