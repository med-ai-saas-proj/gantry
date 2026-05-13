from __future__ import annotations

import json

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.backend_e2e]


def test_admin_token_can_call_admin_me(backend_e2e) -> None:
    response = backend_e2e.admin_request("GET", "/management/v1/admin/me")

    assert response.status_code == 200, response.text
    # The current admin DTO maps Keycloak's display name into `username`.
    assert response.json()["username"] in {"Admin User", "gantry-admin-user"}


def test_normal_user_token_cannot_call_admin_me(backend_e2e) -> None:
    response = backend_e2e.user_request("GET", "/management/v1/admin/me")

    assert response.status_code in {401, 403}, response.text
    assert response.status_code < 500


def test_normal_user_token_contains_fresh_organization_claim(backend_e2e) -> None:
    claims = backend_e2e.user_token_claims()

    organization_claim = claims.get("organization")
    assert organization_claim is not None
    assert backend_e2e.context.org_id in json.dumps(organization_claim)


def test_invalid_and_missing_tokens_do_not_return_5xx(backend_e2e) -> None:
    missing = backend_e2e.request("GET", "/management/v1/admin/me")
    invalid = backend_e2e.request(
        "GET",
        "/management/v1/admin/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert missing.status_code in {401, 403}, missing.text
    assert invalid.status_code in {401, 403}, invalid.text
    assert missing.status_code < 500
    assert invalid.status_code < 500


def test_full_stack_public_catalogs_are_available(backend_e2e) -> None:
    for path in [
        "/management/v1/organizations/permissions",
        "/management/v1/projects/permissions",
        "/management/v1/api-keys/permissions",
    ]:
        response = backend_e2e.request("GET", path)
        assert response.status_code in {200, 401, 403}, response.text
        assert response.status_code < 500
