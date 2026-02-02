#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "python-dotenv",
# ]
# ///
"""
Complete Keycloak realm export with FORCED DEFAULT CREDENTIALS for Dev/Test.
Real password hashes cannot be exported via Admin API for security reasons.
This script sets all user passwords to a known default (e.g., "1").
"""

import os
import sys
import json
import argparse
from pathlib import Path
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

    try:
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError(
                "Failed to get admin token: Response missing access_token"
            )
        return token
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Keycloak at {token_url}: {e}")
        sys.exit(1)


def export_realm_base(
    keycloak_url: str,
    realm: str,
    token: str,
) -> dict:
    """Export realm configuration with groups, roles, and clients."""
    url = f"{keycloak_url}/admin/realms/{realm}/partial-export"
    params = {
        "exportGroupsAndRoles": "true",
        "exportClients": "true",
    }
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    return response.json()


def get_users(keycloak_url: str, realm: str, token: str) -> list:
    """Get all users with full details."""
    url = f"{keycloak_url}/admin/realms/{realm}/users"
    params = {"briefRepresentation": "false", "max": "10000"}
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    return response.json()


def get_client_secret(
    keycloak_url: str,
    realm: str,
    client_id: str,
    token: str,
) -> str:
    """Get secret for a confidential client."""
    url = (
        f"{keycloak_url}/admin/realms/{realm}/clients/"
        f"{client_id}/client-secret"
    )
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("value", "")
    except requests.exceptions.RequestException:
        return ""


def main():
    """Main function to export Keycloak realm."""
    parser = argparse.ArgumentParser(
        description=(
            "Keycloak Realm Export for DEV "
            "(Resets all passwords to '1')"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        "--admin-username",
        default=os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin"),
        help="Admin username",
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin"),
        help="Admin password",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("OUTPUT_DIR", "./asset"),
        help="Output directory",
    )
    parser.add_argument(
        "--output-file",
        help="Output filename",
    )
    parser.add_argument(
        "--default-password",
        default="1",
        help="Password to set for all exported users (default: 1)",
    )

    args = parser.parse_args()

    if not args.output_file:
        args.output_file = f"{args.realm}-realm.json"

    output_dir = Path(args.output_dir)
    output_file = output_dir / args.output_file

    print(f"Exporting realm: {args.realm} from {args.url}")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Authenticate
        print("Authenticating...")
        admin_token = get_admin_token(
            args.url, args.admin_username, args.admin_password
        )

        # Export Realm Config
        print("Exporting realm configuration...")
        realm_data = export_realm_base(args.url, args.realm, admin_token)

        # Fetch Users
        print("Fetching users...")
        users = get_users(args.url, args.realm, admin_token)
        user_count = len(users)
        print(f"Found {user_count} users")

        # Inject Default Password
        # We cannot export real hashes. We inject a plain-text password.
        # Keycloak will hash this upon import.
        print(
            f"Injecting default password '{args.default_password}' "
            f"for all users..."
        )
        for user in users:
            user["credentials"] = [
                {
                    "type": "password",
                    "value": args.default_password,
                    "temporary": False  # User won't be forced to change it
                }
            ]

        realm_data["users"] = users

        # 5. Fetch Client Secrets
        print("Fetching client secrets...")
        for client in realm_data.get("clients", []):
            if not client.get("publicClient", True):
                client_id = client["id"]
                secret = get_client_secret(
                    args.url, args.realm, client_id, admin_token
                )
                if secret:
                    client["secret"] = secret

        # 6. Save to file
        print("Creating final export file...")
        with open(output_file, "w") as f:
            json.dump(realm_data, f, indent=2)

        file_size = output_file.stat().st_size
        size_str = (
            f"{file_size / 1024:.1f}K"
            if file_size < 1024 * 1024
            else f"{file_size / (1024 * 1024):.1f}M"
        )

        print("-" * 50)
        print(f"SUCCESS: Exported to {output_file} ({size_str})")
        print(f"Users processed: {user_count}")
        print(f"All user passwords set to: '{args.default_password}'")
        print("-" * 50)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
