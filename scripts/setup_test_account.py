from src.auth import utils
from src.auth.services.user import UserService
from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

import asyncio
from datetime import UTC, datetime, timedelta


user_service = UserService(CORE_DB_SESSION_SCOPE)
email = "test@test.com"
password = "Thisisaverystrongpassword123"


async def main():
    try:
        user = await user_service.register_user(email=email, password=password)
        print(f"Created a test account with {email=}, {password=}")
    except:
        user = await user_service.get_user_by_email(email)
        print(f"Account already created {email=}, {password=}")
    payload = {
        "user_id": str(user["id"]),
        "email": user["email"],
        "exp": datetime.now(UTC) + timedelta(days=365),
        "iat": datetime.now(UTC),
    }

    api_key = utils.create_token(payload)
    print(f"Created an API key: {api_key=}")


if __name__ == "__main__":
    asyncio.run(main())
