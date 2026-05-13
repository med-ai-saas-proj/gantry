from __future__ import annotations

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.backend_e2e]


def test_admin_dashboard_summary_and_seeded_users_are_available(backend_e2e) -> None:
    summary = backend_e2e.admin_request("GET", "/management/v1/admin/dashboard/summary")
    users = backend_e2e.admin_request("GET", "/management/v1/admin/users", params={"q": "gantry"})

    assert summary.status_code == 200, summary.text
    assert {"organizations", "projects", "api_keys", "users"}.issubset(summary.json())
    assert users.status_code == 200, users.text
    usernames = {item.get("username") for item in users.json().get("results", [])}
    assert "gantry-test-user" in usernames
    assert "gantry-admin-user" in usernames


def test_fresh_organization_detail_settings_and_users_are_available(backend_e2e) -> None:
    org_id = backend_e2e.context.org_id

    detail = backend_e2e.admin_request("GET", f"/management/v1/admin/organizations/{org_id}")
    settings = backend_e2e.admin_request("GET", f"/management/v1/admin/organization-settings/{org_id}")
    users = backend_e2e.admin_request(
        "GET", "/management/v1/admin/organization-users", params={"org_id": org_id}
    )

    assert detail.status_code == 200, detail.text
    assert detail.json()["org_id"] == org_id
    assert settings.status_code == 200, settings.text
    assert {"rate_limit", "spending_limit", "extra"}.issubset(settings.json())
    assert users.status_code == 200, users.text
    assert "results" in users.json()


def test_organization_settings_can_be_updated_without_5xx(backend_e2e) -> None:
    org_id = backend_e2e.context.org_id
    response = backend_e2e.admin_request(
        "PATCH",
        f"/management/v1/admin/organization-settings/{org_id}",
        json={"rate_limit": 1200, "spending_limit": None, "extra": {"e2e.backend": "true"}},
    )

    assert response.status_code == 200, response.text
    assert response.json()["rate_limit"] == 1200
    assert response.json()["extra"].get("e2e.backend") == "true"
