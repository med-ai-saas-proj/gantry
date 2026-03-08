#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "python-dotenv",
# ]
# ///
"""Create RBAC roles for Keycloak client."""

import os
import sys
import argparse

import requests
from dotenv import load_dotenv


load_dotenv()


# Role definitions
ROLES = {
    "super_admin": "Full access to all resources",
    "org.admin": "Organization administrator",
    "org.member": "Organization member",
    "org.viewer": "Organization viewer",
    "member.admin": "Full member management",
    "member.add": "Add members",
    "member.edit": "Edit members",
    "member.delete": "Delete members",
    "member.view": "View members",
    "permission.admin": "Full permission management",
    "permission.create": "Create permissions",
    "permission.edit": "Edit permissions",
    "permission.delete": "Delete permissions",
    "permission.view": "View permissions",
    "apikey.admin": "Full API key management",
    "apikey.create": "Create API keys",
    "apikey.edit": "Edit API keys",
    "apikey.delete": "Delete API keys",
    "apikey.view": "View API keys",
    "user.admin": "Full user management",
    "user.create": "Create users",
    "user.edit": "Edit users",
    "user.delete": "Delete users",
    "user.view": "View users",
    "audit.view": "View audit logs",
    "audit.export": "Export audit logs",
    "settings.admin": "Full settings access",
    "settings.edit": "Edit settings",
    "settings.view": "View settings",
}


def get_admin_token(keycloak_url: str, username: str, password: str) -> str:
    """Get admin authentication token."""
    token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"

    data = {
        "client_id": "admin-cli",
        "username": username,
        "password": password,
        "grant_type": "password",
    }

    response = requests.post(token_url, data=data, timeout=10)
    response.raise_for_status()

    token = response.json().get("access_token")
    if not token:
        raise ValueError("Failed to get admin token")

    return token


def get_client_uuid(
    keycloak_url: str,
    realm: str,
    client_id: str,
    token: str,
) -> str:
    """Get the UUID of a client by its client ID."""
    url = f"{keycloak_url}/admin/realms/{realm}/clients"
    params = {"clientId": client_id}
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()

    clients = response.json()
    if not clients:
        raise ValueError(f"Client '{client_id}' not found")

    return clients[0]["id"]


def role_exists(
    keycloak_url: str,
    realm: str,
    client_uuid: str,
    role_name: str,
    token: str,
) -> bool:
    """Check if a role exists."""
    url = (
        f"{keycloak_url}/admin/realms/{realm}/clients/"
        f"{client_uuid}/roles/{role_name}"
    )
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers, timeout=10)
    return response.status_code == 200


def create_role(
    keycloak_url: str,
    realm: str,
    client_uuid: str,
    role_name: str,
    description: str,
    token: str,
) -> bool:
    """Create a client role."""
    url = f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/roles"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = {
        "name": role_name,
        "description": description,
    }

    response = requests.post(url, json=data, headers=headers, timeout=10)
    return response.status_code == 201


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Create RBAC roles for Keycloak client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
  KEYCLOAK_URL              Keycloak base URL (default: http://localhost:8080)
  REALM                     Keycloak realm (default: dev)
  CLIENT_ID                 Client ID (default: med-ai-saas-app)
  KEYCLOAK_ADMIN_USERNAME   Admin username (default: admin)
  KEYCLOAK_ADMIN_PASSWORD   Admin password (default: admin)
        """,
    )

    parser.add_argument(
        "--url",
        default=os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
        help="Keycloak URL",
    )
    parser.add_argument(
        "--realm",
        default=os.getenv("REALM", "dev"),
        help="Realm name",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("CLIENT_ID", "med-ai-saas-app"),
        help="Client ID",
    )
    parser.add_argument(
        "--admin-username",
        default=os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin"),
        help="Admin username",
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin"),
        help="Admin password",
    )

    args = parser.parse_args()

    print(f"Creating roles for client: {args.client_id}")

    try:
        # Get admin token
        admin_token = get_admin_token(
            args.url, args.admin_username, args.admin_password
        )

        # Get client UUID
        client_uuid = get_client_uuid(
            args.url, args.realm, args.client_id, admin_token
        )

        # Create roles
        created = 0
        skipped = 0

        for role_name, description in ROLES.items():
            if role_exists(
                args.url, args.realm, client_uuid, role_name, admin_token
            ):
                print(f"  Skip: {role_name} (exists)")
                skipped += 1
            else:
                if create_role(
                    args.url,
                    args.realm,
                    client_uuid,
                    role_name,
                    description,
                    admin_token,
                ):
                    print(f"  Created: {role_name}")
                    created += 1
                else:
                    print(f"  Failed: {role_name}")

        print()
        print(
            f"Summary: Created {created} | Skipped {skipped} | "
            f"Total {len(ROLES)}"
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
