from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import factory


PROJECT_UUID = "11111111-1111-1111-1111-111111111111"


class UserInfoFactory(factory.DictFactory):
    id = "user-1"
    username = "api-user"
    email = "api-user@example.com"
    org_uuid = "org-1"
    org_permissions = factory.LazyFunction(
        lambda: [
            "organization.owner",
            "billing.manage",
            "billing.view_usage",
        ]
    )
    project_permissions = factory.LazyFunction(
        lambda: {
            PROJECT_UUID: [
                "project.owner",
                "apikey.read",
                "billing.view_usage",
                "project.file_storage.manage",
                "project.rag.manage",
            ]
        }
    )


class ForbiddenUserInfoFactory(UserInfoFactory):
    org_permissions = factory.LazyFunction(list)
    project_permissions = factory.LazyFunction(dict)


class AdminInfoFactory(factory.DictFactory):
    id = "admin-1"
    username = "admin"
    email = "admin@example.com"


class ApiKeyInfoFactory(factory.DictFactory):
    api_key_id = 10
    api_key_uuid = "api-key-1"
    project_id = 20
    project_uuid = PROJECT_UUID
    organization_uuid = "org-1"
    user_uuid = "user-1"
    hashed_key = "hashed"
    permissions = factory.LazyFunction(
        lambda: [
            "conversation.read",
            "conversation.write",
            "conversation.delete",
            "file.read",
            "file.write",
            "file.delete",
            "rag.read",
            "rag.write",
        ]
    )
    rpm_limit_organization = 1000
    rpm_limit_project = 500
    spending_limit_organization = 100000
    spending_limit_project = 50000


class OrgPayloadFactory(factory.DictFactory):
    org_id = "org-1"
    name = "Org 1"
    owner_id = "user-1"


class ProjectPayloadFactory(factory.DictFactory):
    project_uuid = PROJECT_UUID
    name = "Project 1"
    description = "test project"
    organization_id = "org-1"
    archived = False


class ApiKeyPayloadFactory(factory.DictFactory):
    api_key_id = 10
    api_key_uuid = "api-key-1"
    project_id = 20
    project_uuid = PROJECT_UUID
    name = "Key 1"
    description = "test key"
    hint = "sk_ab...xyz"
    created_at = factory.LazyFunction(lambda: datetime(2026, 1, 1, tzinfo=UTC))
    permissions = factory.LazyFunction(lambda: ["chat.read"])
    disabled = False


def without_keys(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    copied = dict(payload)
    for key in keys:
        copied.pop(key, None)
    return copied
