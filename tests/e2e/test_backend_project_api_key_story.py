from __future__ import annotations

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.backend_e2e]


def test_project_lifecycle_and_user_visibility_flow(backend_e2e) -> None:
    project = backend_e2e.create_project()
    project_uuid = project["project_uuid"]

    detail = backend_e2e.admin_request("GET", f"/management/v1/admin/projects/{project_uuid}")
    update = backend_e2e.admin_request(
        "PUT",
        f"/management/v1/admin/projects/{project_uuid}",
        json={"name": project["name"] + " updated", "description": "updated by e2e"},
    )
    settings = backend_e2e.admin_request(
        "PATCH",
        f"/management/v1/admin/projects/{project_uuid}/settings",
        json={"rate_limit": 60, "spending_limit": None, "extra": {"e2e.project": "true"}},
    )
    user_list = backend_e2e.user_request(
        "GET",
        "/management/v1/projects",
        params={"organization": backend_e2e.context.org_id},
    )

    assert detail.status_code == 200, detail.text
    assert detail.json()["project_uuid"] == project_uuid
    assert update.status_code == 200, update.text
    assert update.json()["name"].endswith(" updated")
    assert settings.status_code == 200, settings.text
    assert settings.json()["rate_limit"] == 60
    assert user_list.status_code == 200, user_list.text
    assert user_list.status_code < 500
    assert project_uuid in {item["project_uuid"] for item in user_list.json().get("results", [])}

    archive = backend_e2e.admin_request("POST", f"/management/v1/admin/projects/{project_uuid}/archive")
    assert archive.status_code == 200, archive.text
    assert archive.json()["archived"] is True

    unarchive = backend_e2e.admin_request("POST", f"/management/v1/admin/projects/{project_uuid}/unarchive")
    assert unarchive.status_code == 200, unarchive.text
    assert unarchive.status_code < 500
    assert unarchive.json()["archived"] is False


def test_admin_permission_update_affects_user_project_permissions(backend_e2e) -> None:
    project = backend_e2e.create_project(name_prefix="e2e-permission")
    project_uuid = project["project_uuid"]
    user_id = backend_e2e.find_user_id("gantry-test-user")

    response = backend_e2e.admin_request(
        "PUT",
        f"/management/v1/admin/users/{user_id}/permissions",
        json={
            "organization_permissions": ["organization.owner"],
            "project_permissions": [
                {"project_uuid": project_uuid, "permissions": ["project.settings.read", "apikey.read"]}
            ],
        },
    )
    backend_e2e.refresh_user_token()
    permissions = backend_e2e.user_request(
        "GET", f"/management/v1/projects/{project_uuid}/users/{user_id}/permissions"
    )

    assert response.status_code == 200, response.text
    summary = response.json()["permissions"]
    assert "organization.owner" in summary["organization_permissions"]
    assert any(
        (item.get("project_uuid") or item.get("id")) == project_uuid
        for item in summary["project_permissions"]
    )
    assert permissions.status_code in {200, 401, 403, 404}, permissions.text
    assert permissions.status_code < 500


def test_admin_scoped_org_and_project_permission_routes_preserve_other_scopes(
    backend_e2e,
) -> None:
    project = backend_e2e.create_project(name_prefix="e2e-scoped-permission")
    project_uuid = project["project_uuid"]
    user_id = backend_e2e.find_user_id("gantry-test-user")

    org_update = backend_e2e.admin_request(
        "PUT",
        (
            f"/management/v1/admin/organizations/{backend_e2e.context.org_id}"
            f"/users/{user_id}/permissions"
        ),
        json={"permissions": ["organization.owner"]},
    )
    project_update = backend_e2e.admin_request(
        "PUT",
        f"/management/v1/admin/projects/{project_uuid}/users/{user_id}/permissions",
        json={"permissions": ["project.settings.read", "apikey.read"]},
    )
    summary = backend_e2e.admin_request(
        "GET",
        f"/management/v1/admin/users/{user_id}/permissions",
    )

    assert org_update.status_code == 200, org_update.text
    assert project_update.status_code == 200, project_update.text
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["organization_permissions"] == ["organization.owner"]
    assert any(
        item["project_uuid"] == project_uuid
        and set(item["permissions"]) == {"project.settings.read", "apikey.read"}
        for item in payload["project_permissions"]
    )


def test_api_key_lifecycle_by_uuid_and_disabled_key_rejection(backend_e2e) -> None:
    project = backend_e2e.create_project(name_prefix="e2e-api-key")
    project_uuid = project["project_uuid"]
    created = backend_e2e.create_api_key(project_uuid, permissions=["conversation.read", "conversation.write"])
    api_key_uuid = created["api_key_uuid"]
    raw_key = created["key"]

    listed = backend_e2e.admin_request(
        "GET", "/management/v1/admin/api-keys", params={"project_id": project_uuid}
    )
    fetched = backend_e2e.admin_request("GET", f"/management/v1/admin/api-keys/{api_key_uuid}")
    disabled_update = backend_e2e.admin_request(
        "PUT",
        f"/management/v1/admin/api-keys/{api_key_uuid}",
        json={
            "name": "e2e key disabled",
            "description": "disabled by e2e",
            "permissions": ["chat.read"],
            "disabled": True,
        },
    )
    listed_disabled = backend_e2e.admin_request(
        "GET",
        "/management/v1/admin/api-keys",
        params={"project_id": project_uuid, "disabled": True},
    )
    fetched_disabled = backend_e2e.admin_request(
        "GET",
        f"/management/v1/admin/api-keys/{api_key_uuid}",
        params={"disabled": True},
    )
    updated = backend_e2e.admin_request(
        "PUT",
        f"/management/v1/admin/api-keys/{api_key_uuid}",
        json={
            "name": "e2e key updated",
            "description": "updated",
            "permissions": ["chat.read"],
            "disabled": False,
        },
    )
    service_call_before_delete = backend_e2e.request(
        "POST",
        "/service/v1/conversations/sequence/",
        headers={"X-Api-Key": raw_key},
        json={"extra_metadata": {"source": "backend-e2e"}, "messages": None},
    )

    assert listed.status_code == 200, listed.text
    assert api_key_uuid in {item["api_key_uuid"] for item in listed.json().get("results", [])}
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["api_key_uuid"] == api_key_uuid
    assert disabled_update.status_code == 200, disabled_update.text
    assert disabled_update.json()["disabled"] is True
    assert listed_disabled.status_code == 200, listed_disabled.text
    assert api_key_uuid in {
        item["api_key_uuid"]
        for item in listed_disabled.json().get("results", [])
        if item.get("disabled") is True
    }
    assert fetched_disabled.status_code == 200, fetched_disabled.text
    assert fetched_disabled.json()["disabled"] is True
    assert updated.status_code == 200, updated.text
    assert updated.json()["permissions"] == ["chat.read"]
    assert updated.json()["disabled"] is False
    assert service_call_before_delete.status_code in {201, 400, 401, 403}, service_call_before_delete.text
    assert service_call_before_delete.status_code < 500

    deleted = backend_e2e.admin_request("DELETE", f"/management/v1/admin/api-keys/{api_key_uuid}")
    rejected = backend_e2e.request(
        "POST",
        "/service/v1/conversations/sequence/",
        headers={"X-Api-Key": raw_key},
        json={"extra_metadata": {"source": "backend-e2e"}, "messages": None},
    )

    assert deleted.status_code == 200, deleted.text
    assert rejected.status_code in {401, 403, 404}, rejected.text
    assert rejected.status_code < 500
