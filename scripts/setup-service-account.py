#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "python-dotenv",
# ]
# ///
"""Setup Keycloak service account for backend role management."""

import os
import sys
import argparse
from typing import Optional

import requests
from dotenv import load_dotenv


load_dotenv()


class KeycloakServiceAccountSetup:
    """Keycloak service account configuration manager."""

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        service_client_id: str,
        admin_username: str,
        admin_password: str,
    ):
        """Initialize setup with Keycloak connection and admin credentials."""
        self.keycloak_url = keycloak_url
        self.realm = realm
        self.service_client_id = service_client_id
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.admin_token: Optional[str] = None

    def authenticate(self) -> str:
        """Get admin authentication token."""
        print("[1/5] Authenticating...")

        token_url = (
            f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"
        )
        data = {
            "client_id": "admin-cli",
            "username": self.admin_username,
            "password": self.admin_password,
            "grant_type": "password",
        }

        try:
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()

            token = response.json().get("access_token")
            if not token:
                raise ValueError("Failed to get admin token")

            self.admin_token = token
            return token

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Authentication failed: {e}") from e

    def get_client_uuid(self) -> Optional[str]:
        """Get client UUID if it exists."""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/clients"
        params = {"clientId": self.service_client_id}
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        response = requests.get(
            url=url, params=params, headers=headers, timeout=10
        )
        response.raise_for_status()

        clients = response.json()
        if clients:
            return clients[0]["id"]
        return None

    def create_service_account_client(self) -> str:
        """Create a new service account client."""
        print("  Creating service account client...")

        url = f"{self.keycloak_url}/admin/realms/{self.realm}/clients"
        headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json",
        }

        client_config = {
            "clientId": self.service_client_id,
            "name": "Backend Service Account",
            "description": "Service account for backend role management",
            "enabled": True,
            "serviceAccountsEnabled": True,
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "publicClient": False,
            "protocol": "openid-connect",
        }

        response = requests.post(
            url=url, json=client_config, headers=headers, timeout=10
        )

        if response.status_code != 201:
            raise ValueError(
                f"Failed to create client (HTTP {response.status_code})"
            )

        # Get the created client UUID
        client_uuid = self.get_client_uuid()
        if not client_uuid:
            raise ValueError("Failed to retrieve created client UUID")

        print(f"  Created: {client_uuid}")
        return client_uuid

    def ensure_client_exists(self) -> str:
        """Ensure service account client exists, create if not."""
        print("[2/5] Checking if client exists...")

        client_uuid = self.get_client_uuid()

        if client_uuid:
            print(f"  Client exists: {client_uuid}")
            return client_uuid

        return self.create_service_account_client()

    def get_client_secret(self, client_uuid: str) -> str:
        """Get client secret."""
        print("[3/5] Getting client secret...")

        url = (
            f"{self.keycloak_url}/admin/realms/{self.realm}/clients/"
            f"{client_uuid}/client-secret"
        )
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        secret = response.json().get("value")
        if not secret:
            raise ValueError("Failed to get client secret")

        return secret

    def get_service_account_user_id(self, client_uuid: str) -> str:
        """Get service account user ID."""
        print("[4/5] Getting service account user...")

        url = (
            f"{self.keycloak_url}/admin/realms/{self.realm}/clients/"
            f"{client_uuid}/service-account-user"
        )
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        user_id = response.json().get("id")
        if not user_id:
            raise ValueError("Failed to get service account user")

        return user_id

    def get_realm_management_client_uuid(self) -> str:
        """Get realm-management client UUID."""
        url = f"{self.keycloak_url}/admin/realms/{self.realm}/clients"
        params = {"clientId": "realm-management"}
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        clients = response.json()
        if not clients:
            raise ValueError("Failed to get realm-management client")

        return clients[0]["id"]

    def get_realm_management_role(
        self, realm_mgmt_uuid: str, role_name: str
    ) -> dict:
        """Get a specific realm-management role."""
        url = (
            f"{self.keycloak_url}/admin/realms/{self.realm}/clients/"
            f"{realm_mgmt_uuid}/roles/{role_name}"
        )
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()

    def assign_realm_management_roles(
        self,
        service_user_id: str,
        realm_mgmt_uuid: str,
    ) -> bool:
        """Assign realm-management roles to service account."""
        print("[5/5] Assigning permissions...")

        # Roles to assign
        role_names = [
            "manage-users",  # Assign/remove roles
            "view-users",  # View user info
            "view-clients",  # Get client details
            "manage-realm",  # Organization admin API
        ]

        # Get role representations
        roles = []
        for role_name in role_names:
            try:
                role = self.get_realm_management_role(
                    realm_mgmt_uuid, role_name
                )
                roles.append(role)
            except requests.exceptions.RequestException as e:
                print(f"  Warning: Could not get role {role_name}: {e}")

        if not roles:
            raise ValueError("No roles could be retrieved")

        # Assign roles
        url = (
            f"{self.keycloak_url}/admin/realms/{self.realm}/users/"
            f"{service_user_id}/role-mappings/clients/{realm_mgmt_uuid}"
        )
        headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=roles, headers=headers, timeout=10)

        if response.status_code in (200, 204):
            print("  Permissions assigned successfully")
            return True
        else:
            print(
                "  Warning: Failed to assign permissions "
                f"(HTTP {response.status_code})"
            )
            print(
                "  You may need to assign them manually in "
                "Keycloak Admin Console"
            )
            return False

    def setup(self) -> tuple[str, str]:
        """Run complete service account setup."""
        print(f"Setting up service account for: {self.realm}")
        print(f"Service client: {self.service_client_id}")
        print()

        # Authenticate
        self.authenticate()

        # Ensure client exists
        client_uuid = self.ensure_client_exists()

        # Get client secret
        client_secret = self.get_client_secret(client_uuid)

        # Get service account user
        service_user_id = self.get_service_account_user_id(client_uuid)

        # Get realm-management client
        realm_mgmt_uuid = self.get_realm_management_client_uuid()

        # Assign permissions
        self.assign_realm_management_roles(service_user_id, realm_mgmt_uuid)

        return self.service_client_id, client_secret


def print_success_message(
    keycloak_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
):
    """Print success message with configuration details."""
    print()
    print("=" * 42)
    print("Service Account Setup Complete!")
    print("=" * 42)
    print()
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret}")
    print()
    print("Assigned Permissions:")
    print("  • manage-users (assign/remove roles)")
    print("  • view-users (view user info)")
    print("  • view-clients (get client details)")
    print("  • manage-realm (organization admin API)")
    print()
    print("Add to your .env file:")
    print("-" * 42)
    print(f"KEYCLOAK_SERVICE_CLIENT_ID={client_id}")
    print(f"KEYCLOAK_SERVICE_CLIENT_SECRET={client_secret}")
    print("-" * 42)
    print()
    print("Test the service account:")
    print(
        f'  curl -X POST "{keycloak_url}/realms/{realm}/'
        'protocol/openid-connect/token" \\'
    )
    print(f'    -d "client_id={client_id}" \\')
    print(f'    -d "client_secret={client_secret}" \\')
    print('    -d "grant_type=client_credentials"')
    print()


def main():
    """Run the service account setup CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Setup Keycloak service account for backend role management"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script creates a service account client in Keycloak with permissions
to manage users and roles. Service accounts use client_credentials grant
type and are ideal for backend services that need to interact with Keycloak
APIs without user context.

Permissions granted:
  • manage-users  - Assign/remove roles to users
  • view-users    - View user information
  • view-clients  - Get client details
  • manage-realm  - Organization admin operations

Environment variables:
  KEYCLOAK_URL                Keycloak base URL (default: http://localhost:8080)
  REALM                       Keycloak realm (default: dev)
  SERVICE_CLIENT_ID           Service client ID (default: med-ai-saas-backend)
  KEYCLOAK_ADMIN_USERNAME     Admin username (default: admin)
  KEYCLOAK_ADMIN_PASSWORD     Admin password (default: admin)

Examples:
  # Setup with defaults
  %(prog)s

  # Setup for production realm
  %(prog)s --realm production --service-client-id prod-backend

  # Custom admin credentials
  %(prog)s --admin-username myadmin --admin-password mypass
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
        "--service-client-id",
        default=os.getenv("SERVICE_CLIENT_ID", "med-ai-saas-backend"),
        help="Service account client ID",
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

    try:
        # Setup service account
        setup = KeycloakServiceAccountSetup(
            keycloak_url=args.url,
            realm=args.realm,
            service_client_id=args.service_client_id,
            admin_username=args.admin_username,
            admin_password=args.admin_password,
        )

        client_id, client_secret = setup.setup()

        # Print success message
        print_success_message(
            args.url,
            args.realm,
            client_id,
            client_secret,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
