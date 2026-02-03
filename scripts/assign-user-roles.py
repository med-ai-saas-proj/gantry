#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "python-dotenv",
# ]
# ///
"""Assign client-specific roles to a user in Keycloak."""

import os
import sys
import argparse
from typing import List
import requests
from dotenv import load_dotenv

load_dotenv()


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


def get_user_id(
    keycloak_url: str,
    realm: str,
    email: str,
    token: str,
) -> str:
    """Find user ID by email."""
    url = f"{keycloak_url}/admin/realms/{realm}/users"
    params = {"email": email, "exact": "true"}
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()

    users = response.json()
    if not users:
        raise ValueError(f"User '{email}' not found")

    return users[0]["id"]


def get_available_roles(
    keycloak_url: str,
    realm: str,
    client_uuid: str,
    token: str,
) -> List[dict]:
    """Get all available client roles."""
    url = f"{keycloak_url}/admin/realms/{realm}/clients/{client_uuid}/roles"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    return response.json()


def assign_roles(
    keycloak_url: str,
    realm: str,
    user_id: str,
    client_uuid: str,
    roles: List[dict],
    token: str,
) -> bool:
    """Assign roles to user."""
    url = (
        f"{keycloak_url}/admin/realms/{realm}/users/{user_id}/"
        f"role-mappings/clients/{client_uuid}"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=roles, headers=headers, timeout=10)
    return response.status_code == 204


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Assign client-specific roles to a user in Keycloak",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s user@example.com member.add member.edit
  %(prog)s user@example.com super_admin
  %(prog)s --realm prod admin@example.com user.admin audit.view

Common roles:
  super_admin
  member.admin, member.add, member.edit, member.delete, member.view
  permission.admin, apikey.admin, user.admin, audit.view, settings.admin

Environment variables:
  KEYCLOAK_URL              Keycloak base URL (default: http://localhost:8080)
  REALM                     Keycloak realm (default: dev)
  CLIENT_ID                 Client ID (default: med-ai-saas-app)
  KEYCLOAK_ADMIN_USERNAME   Admin username (default: admin)
  KEYCLOAK_ADMIN_PASSWORD   Admin password (default: admin)
        """,
    )

    parser.add_argument(
        "user_email",
        help="User email address",
    )
    parser.add_argument(
        "roles",
        nargs="+",
        help="Roles to assign",
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

    print(f"Assigning roles to: {args.user_email}")
    print(f"Roles: {', '.join(args.roles)}")

    try:
        # Get admin token
        admin_token = get_admin_token(
            args.url, args.admin_username, args.admin_password
        )

        # Get client UUID
        client_uuid = get_client_uuid(
            args.url, args.realm, args.client_id, admin_token
        )

        # Get user ID
        user_id = get_user_id(
            args.url, args.realm, args.user_email, admin_token
        )

        # Get available roles
        available_roles = get_available_roles(
            args.url, args.realm, client_uuid, admin_token
        )
        available_roles_map = {role["name"]: role for role in available_roles}

        # Build roles to assign
        roles_to_assign = []
        missing_roles = []

        for role_name in args.roles:
            if role_name in available_roles_map:
                role_data = available_roles_map[role_name]
                roles_to_assign.append({
                    "id": role_data["id"],
                    "name": role_data["name"],
                })
            else:
                missing_roles.append(role_name)

        # Check for missing roles
        if missing_roles:
            print(
                f"Error: Roles not found: {', '.join(missing_roles)}",
                file=sys.stderr,
            )
            print(
                "Run setup_keycloak_roles.py to create roles first",
                file=sys.stderr,
            )
            sys.exit(1)

        # Check if there are valid roles to assign
        if not roles_to_assign:
            print("Error: No valid roles to assign", file=sys.stderr)
            sys.exit(1)

        # Assign roles
        if assign_roles(
            args.url,
            args.realm,
            user_id,
            client_uuid,
            roles_to_assign,
            admin_token,
        ):
            print(f"Success: Roles assigned to {args.user_email}")
            print()
            print(
                f"Verify: {args.url}/admin/master/console/"
                f"#{args.realm}/users/{user_id}/role-mapping"
            )
        else:
            print("Error: Failed to assign roles", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
