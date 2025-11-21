import asyncio
from datetime import UTC, datetime, timedelta

from src.auth.factories import getUserService


username = "test"
email = "test@test.com"
password = "Thisisaverystrongpassword123"


async def main():
    user_service = getUserService()
    try:
        user = await user_service.emailRegister(username, email, password)
        print(f"Created a test account with {email=}, {password=}")
    except:
        user = await user_service.emailLogin(email, password)
        print(f"Account already created {email=}, {password=}")


if __name__ == "__main__":
    asyncio.run(main())
