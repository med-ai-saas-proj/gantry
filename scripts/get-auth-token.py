#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "python-dotenv",
# ]
# ///
"""Get authentication token from Keycloak using password grant."""

import os
import sys
import json
import argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()


def get_auth_token(
    keycloak_url: str,
    realm: str,
    client_id: str,
    username: str,
    password: str,
) -> dict:
    """Request authentication token from Keycloak."""
    token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"

    data = {
        "client_id": client_id,
        "username": username,
        "password": password,
        "grant_type": "password",
    }

    try:
        response = requests.post(
            token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to {keycloak_url}", file=sys.stderr)
        print("Ensure Keycloak is running", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print("Error: Authentication failed", file=sys.stderr)
        try:
            error_data = e.response.json()
            print(json.dumps(error_data, indent=2), file=sys.stderr)

            if error_data.get("error") == "unauthorized_client":
                print(
                    "\nFix: Enable 'Direct Access Grants' in Keycloak",
                    file=sys.stderr,
                )
                print(f"  1. Go to: {keycloak_url}/admin", file=sys.stderr)
                print(
                    f"  2. Navigate: {realm} → Clients → "
                    f"{client_id} → Settings",
                    file=sys.stderr
                )
                print("  3. Enable: Direct access grants", file=sys.stderr)
                print("  4. Save", file=sys.stderr)
        except Exception:
            print(str(e), file=sys.stderr)
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Get authentication token from Keycloak",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
  KEYCLOAK_URL          Keycloak base URL (default: http://localhost:8080)
  REALM                 Keycloak realm (default: dev)
  CLIENT_ID             Client ID (default: med-ai-saas-app)
  KEYCLOAK_USERNAME     Username for authentication
  KEYCLOAK_PASSWORD     Password for authentication

Examples:
  %(prog)s user@example.com mypassword
  KEYCLOAK_USERNAME=user@example.com KEYCLOAK_PASSWORD=mypass %(prog)s
        """,
    )

    parser.add_argument(
        "username",
        nargs="?",
        help="Username (or set KEYCLOAK_USERNAME)",
    )
    parser.add_argument(
        "password",
        nargs="?",
        help="Password (or set KEYCLOAK_PASSWORD)",
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

    args = parser.parse_args()

    username = args.username or os.getenv("KEYCLOAK_USERNAME")
    password = args.password or os.getenv("KEYCLOAK_PASSWORD")

    if not username or not password:
        parser.print_help()
        print("\nCurrent config:", file=sys.stderr)
        print(f"  URL: {args.url}", file=sys.stderr)
        print(f"  Realm: {args.realm}", file=sys.stderr)
        print(f"  Client: {args.client_id}", file=sys.stderr)
        sys.exit(1)

    # Get token
    response = get_auth_token(
        args.url,
        args.realm,
        args.client_id,
        username,
        password,
    )

    access_token = response.get("access_token")
    # refresh_token = response.get("refresh_token")
    expires_in = response.get("expires_in", 0)

    if not access_token:
        print("Error: Failed to get access token", file=sys.stderr)
        print(json.dumps(response, indent=2), file=sys.stderr)
        sys.exit(1)

    # Save token
    token_file = Path("/tmp/keycloak_token.txt")
    token_file.write_text(access_token)

    # Output
    print("Access Token:")
    print(access_token)
    print()
    print(f"Expires in: {expires_in} seconds ({expires_in // 60} minutes)")
    print(f"Saved to: {token_file}")
    print()
    print("Usage:")
    print(f'  export AUTH_TOKEN="{access_token}"')
    print("  # or")
    print(f"  export AUTH_TOKEN=$(cat {token_file})")
    print()
    print("Test:")
    print(
        '  curl -H "Authorization: Bearer $AUTH_TOKEN" '
        "http://localhost:8000/api/endpoint"
    )


if __name__ == "__main__":
    main()
