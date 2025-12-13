#!/usr/bin/env -S uv run
import json
import asyncio

from keycloak import KeycloakAdmin


admin_username = "admin"
admin_password = "admin"


async def main():
    admin_client = KeycloakAdmin(
        server_url="http://localhost:8080/",
        username=admin_username,
        password=admin_password,
        realm_name="master",
    )

    with open("asset/dev-realm.json") as f:
        dev_realm_config = json.load(f)

    admin_client.create_realm(dev_realm_config, skip_exists=True)
    admin_client.connection.realm_name = "dev-realm"

    admin_client.create_user(
        {
            "email": "test@test.com",
            "emailVerified": True,
            "username": "test",
            "enabled": True,
            "firstName": "Example",
            "lastName": "Example",
            "credentials": [
                {
                    "type": "password",
                    "value": "password",
                }
            ],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
