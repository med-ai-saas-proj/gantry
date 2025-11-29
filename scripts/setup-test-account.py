from src.auth.factories import getUserService

import asyncio


username = "test"
email = "test@test.com"
password = "Thisisastrongpassword123"


async def main():
    user_service = getUserService()
    try:
        user_ = await user_service.emailRegister(username, email, password)
        user = user_.unwrap()
        print(f"Created a test account with {user.email}, {user.id}")
    except Exception as e:
        print("Failed to create test account:", e)


if __name__ == "__main__":
    asyncio.run(main())
