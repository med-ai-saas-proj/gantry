from __future__ import annotations

from uuid import uuid4

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.backend_e2e]


def test_invitation_outbox_is_available_for_email_verification(backend_e2e) -> None:
    messages = backend_e2e.mailpit_messages()

    assert "messages" in messages


def test_organization_invitation_path_is_safe_and_sends_email_when_user_has_org_claim(
    backend_e2e,
) -> None:
    org_id = backend_e2e.context.org_id
    email = f"e2e-invite-{uuid4().hex}@example.com"

    response = backend_e2e.user_request(
        "POST",
        f"/management/v1/organizations/{org_id}/invitations",
        json={"email": email},
    )
    messages = backend_e2e.mailpit_messages()

    assert response.status_code in {200, 401, 403}, response.text
    assert response.status_code < 500
    if response.status_code == 200:
        serialized = str(messages)
        assert email in serialized
        assert "http://localhost:3000" in serialized or "invite" in serialized.lower()
    else:
        assert response.json().get("code") in {
            "missing_organization_claim",
            "forbidden",
            "missing_org_context",
        }
