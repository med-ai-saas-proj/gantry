#!/usr/bin/env -S uv run

import asyncio

from keycloak import KeycloakOpenID


async def main():
    admin_client = KeycloakOpenID(
        server_url="http://localhost:8080/",
        realm_name="dev-realm",
        client_id="backend-app",
        client_secret_key="zYT1DhwT5xs97KcYqWaQvZF4kT6eor4y",
    )
    token = admin_client.token("test-user", "Thisisastrongpassword123")
    print(token)


if __name__ == "__main__":
    asyncio.run(main())
