from __future__ import annotations

from datetime import UTC, datetime
from functools import wraps
from inspect import iscoroutinefunction
from types import SimpleNamespace
from typing import Any

from pyrusult import Ok

from gantry.management.billing.models import TransactionStatus
from gantry.service.conversation.models import ConversationType
from tests.factories import ApiKeyInfoFactory, ApiKeyPayloadFactory, OrgPayloadFactory, ProjectPayloadFactory


NOW = datetime(2026, 1, 1, tzinfo=UTC)
PROJECT_UUID = "11111111-1111-1111-1111-111111111111"


class ConfigurableFake:
    """Small test double base that can force domain failures per method."""

    def fail_next(self, method_name: str, error: Exception) -> None:
        failures = getattr(self, "_failures", None)
        if failures is None:
            failures = {}
            object.__setattr__(self, "_failures", failures)
        failures.setdefault(method_name, []).append(error)

    def _pop_failure(self, method_name: str) -> Exception | None:
        failures = getattr(self, "_failures", {})
        queued = failures.get(method_name) or []
        if not queued:
            return None
        return queued.pop(0)

    def __getattribute__(self, name: str):
        attr = object.__getattribute__(self, name)
        if name.startswith("_") or name in {"fail_next"} or not callable(attr):
            return attr

        if iscoroutinefunction(attr):

            @wraps(attr)
            async def async_wrapper(*args, **kwargs):
                failure = self._pop_failure(name)
                if failure is not None:
                    raise failure
                return await attr(*args, **kwargs)

            return async_wrapper

        @wraps(attr)
        def sync_wrapper(*args, **kwargs):
            failure = self._pop_failure(name)
            if failure is not None:
                raise failure
            return attr(*args, **kwargs)

        return sync_wrapper


def api_key_payload(
    api_key_uuid: str = "api-key-1",
    project_uuid: str = PROJECT_UUID,
) -> dict[str, Any]:
    return ApiKeyPayloadFactory(api_key_uuid=api_key_uuid, project_uuid=project_uuid)


def project_payload(project_uuid: str = PROJECT_UUID) -> dict[str, Any]:
    return ProjectPayloadFactory(project_uuid=project_uuid)


def org_payload(org_id: str = "org-1") -> dict[str, Any]:
    return OrgPayloadFactory(org_id=org_id)


class FakeProjectService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def authorizeProjectPermission(self, **kwargs):
        self.calls.append(("authorizeProjectPermission", kwargs))
        return Ok(True)

    async def isProjectArchived(self, project_uuid: str):
        self.calls.append(("isProjectArchived", project_uuid))
        return Ok(False)

    async def listUserProjects(self, **kwargs):
        self.calls.append(("listUserProjects", kwargs))
        return Ok({"total": 1, "results": [project_payload()]})

    async def listOrgProjects(self, **kwargs):
        self.calls.append(("listOrgProjects", kwargs))
        return Ok({"total": 1, "results": [project_payload()]})

    async def createProject(self, **kwargs):
        self.calls.append(("createProject", kwargs))
        return Ok(project_payload())

    async def getProject(self, **kwargs):
        self.calls.append(("getProject", kwargs))
        return Ok(project_payload(kwargs.get("project_uuid", PROJECT_UUID)))

    async def updateProject(self, **kwargs):
        self.calls.append(("updateProject", kwargs))
        return Ok(project_payload(kwargs.get("project_uuid", PROJECT_UUID)))

    async def getProjectSettings(self, project_uuid: str):
        self.calls.append(("getProjectSettings", project_uuid))
        return Ok({"rate_limit": 120, "spending_limit": 5000, "extra": {"mode": "burst"}})

    async def updateProjectSettings(self, **kwargs):
        self.calls.append(("updateProjectSettings", kwargs))
        return Ok({"rate_limit": kwargs["rate_limit"], "spending_limit": kwargs["spending_limit"], "extra": kwargs["extra"]})

    async def listProjectUsers(self, **kwargs):
        self.calls.append(("listProjectUsers", kwargs))
        return Ok({"total": 1, "results": [{"id": "user-2", "username": "bob", "email": "bob@example.com"}]})

    async def addUserToProject(self, **kwargs):
        self.calls.append(("addUserToProject", kwargs))
        return Ok(True)

    async def removeUserFromProject(self, **kwargs):
        self.calls.append(("removeUserFromProject", kwargs))
        return Ok(True)

    async def getUserPermissions(self, **kwargs):
        self.calls.append(("getUserPermissions", kwargs))
        return Ok({"permissions": ["project.settings.read"]})

    async def updateUserPermissions(self, **kwargs):
        self.calls.append(("updateUserPermissions", kwargs))
        return Ok({"permissions": kwargs["permissions"]})

    async def setProjectArchived(self, project_uuid: str, archived: bool):
        self.calls.append(("setProjectArchived", {"project_uuid": project_uuid, "archived": archived}))
        return Ok(SimpleNamespace(id=project_uuid, archived=archived))


class FakeApiKeyService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def verifyApiKey(self, api_key: str, permissions: list[str]):
        self.calls.append(("verifyApiKey", {"api_key": api_key, "permissions": permissions}))
        return Ok(api_key_info_payload())

    async def parseApiKey(self, api_key: str):
        self.calls.append(("parseApiKey", api_key))
        return Ok(api_key_info_payload())

    async def rateLimit(self, api_key_info: dict[str, Any]):
        self.calls.append(("rateLimit", api_key_info["api_key_uuid"]))
        return Ok(True)

    async def getApiKeyInternalIds(self, api_key_uuid: str):
        self.calls.append(("getApiKeyInternalIds", api_key_uuid))
        return Ok({"api_key_id": 10, "project_id": 20})

    def getPermissionCatalog(self):
        return {"total": 1, "results": [{"id": "chat.read", "name": "Chat Read", "description": "Read chat"}]}

    async def getApiKeyProjectUuid(self, api_key_uuid: str):
        self.calls.append(("getApiKeyProjectUuid", api_key_uuid))
        return Ok(PROJECT_UUID)

    async def getApiKeys(self, project_uuid: str, disabled: bool | None = None):
        self.calls.append(
            (
                "getApiKeys",
                {"project_uuid": project_uuid, "disabled": disabled},
            )
        )
        payload = api_key_payload(project_uuid=project_uuid)
        if disabled is not None:
            payload["disabled"] = disabled
        return Ok({"total": 1, "results": [payload]})

    async def createApiKey(self, **kwargs):
        self.calls.append(("createApiKey", kwargs))
        payload = api_key_payload(project_uuid=kwargs["project_uuid"])
        payload["key"] = "sk_api-key-1.secret"
        return Ok(payload)

    async def getApiKey(self, api_key_uuid: str):
        self.calls.append(("getApiKey", api_key_uuid))
        return Ok(api_key_payload(api_key_uuid=api_key_uuid))

    async def updateApiKey(self, **kwargs):
        self.calls.append(("updateApiKey", kwargs))
        payload = api_key_payload(api_key_uuid=kwargs["api_key_uuid"])
        payload["name"] = kwargs["name"]
        payload["description"] = kwargs["description"]
        payload["permissions"] = kwargs["permissions"]
        if kwargs.get("disabled") is not None:
            payload["disabled"] = kwargs["disabled"]
        return Ok(payload)

    async def setApiKeyDisabled(self, **kwargs):
        self.calls.append(("setApiKeyDisabled", kwargs))
        payload = api_key_payload(api_key_uuid=kwargs["api_key_uuid"])
        payload["disabled"] = kwargs["disabled"]
        return Ok(payload)

    async def deleteApiKey(self, api_key_uuid: str):
        self.calls.append(("deleteApiKey", api_key_uuid))
        return Ok(True)


class FakeOrgService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def getOrgInfo(self, org_id: str):
        self.calls.append(("getOrgInfo", org_id))
        return Ok(org_payload(org_id))

    async def listUserOrgs(
        self,
        user_id: str,
        limit: int,
        offset: int,
        q: str | None,
    ):
        self.calls.append(
            (
                "listUserOrgs",
                {
                    "user_id": user_id,
                    "limit": limit,
                    "offset": offset,
                    "q": q,
                },
            )
        )
        return Ok({"total": 1, "results": [org_payload()]})

    async def createOrgForUser(
        self,
        user_id: str,
        name: str,
        alias: str | None,
    ):
        self.calls.append(
            (
                "createOrgForUser",
                {"user_id": user_id, "name": name, "alias": alias},
            )
        )
        payload = org_payload("org-created")
        payload["name"] = name
        payload["alias"] = alias
        payload["owner_id"] = user_id
        return Ok(payload)

    async def updateOrgInfo(self, **kwargs):
        self.calls.append(("updateOrgInfo", kwargs))
        payload = org_payload(kwargs["org_id"])
        payload["name"] = kwargs["name"]
        return Ok(payload)

    async def requestDeleteOrg(self, org_id: str):
        self.calls.append(("requestDeleteOrg", org_id))
        return Ok({"id": org_id, "requested_at": "2026-01-01T00:00:00", "cancel_before": "2026-01-31T00:00:00"})

    async def cancelDeleteOrg(self, org_id: str):
        self.calls.append(("cancelDeleteOrg", org_id))
        return Ok(True)

    async def getSettings(self, org_id: str):
        self.calls.append(("getSettings", org_id))
        return Ok({"rate_limit": 100, "spending_limit": 1000, "extra": {"tier": "pro"}})

    async def updateSettings(self, org_id: str, rate_limit, spending_limit, extra):
        self.calls.append(("updateSettings", {"org_id": org_id, "rate_limit": rate_limit, "spending_limit": spending_limit, "extra": extra}))
        return Ok({"rate_limit": rate_limit, "spending_limit": spending_limit, "extra": extra})

    async def getUsers(self, org_id: str, offset: int, limit: int, q: str | None):
        self.calls.append(("getUsers", {"org_id": org_id, "offset": offset, "limit": limit, "q": q}))
        return Ok({"total": 1, "results": [{"id": "user-1", "username": "alice", "email": "alice@example.com"}]})

    async def removeUser(self, org_id: str, user_id: str):
        self.calls.append(("removeUser", {"org_id": org_id, "user_id": user_id}))
        return Ok(True)

    async def getInvitations(self, org_id: str):
        self.calls.append(("getInvitations", org_id))
        return Ok({"results": [{"id": "inv-1", "email": "a@example.com", "status": "PENDING"}]})

    async def createInvitation(self, org_id: str, email: str):
        self.calls.append(("createInvitation", {"org_id": org_id, "email": email}))
        return Ok(True)

    async def getInvitation(self, org_id: str, invitation_id: str):
        self.calls.append(("getInvitation", {"org_id": org_id, "invitation_id": invitation_id}))
        return Ok({"id": invitation_id, "email": "a@example.com", "status": "PENDING"})

    async def deleteInvitation(self, org_id: str, invitation_id: str):
        self.calls.append(("deleteInvitation", {"org_id": org_id, "invitation_id": invitation_id}))
        return Ok(True)

    async def resendInvitation(self, org_id: str, invitation_id: str):
        self.calls.append(("resendInvitation", {"org_id": org_id, "invitation_id": invitation_id}))
        return Ok({"id": "inv-2", "email": "a@example.com", "status": "PENDING"})

    async def ensureCanReadUserPermissions(self, **kwargs):
        self.calls.append(("ensureCanReadUserPermissions", kwargs))
        return Ok(True)

    async def getUserPermissions(self, org_id: str, user_id: str):
        self.calls.append(("getUserPermissions", {"org_id": org_id, "user_id": user_id}))
        return Ok({"permissions": ["organization.settings.read"]})

    async def updateUserPermissions(self, **kwargs):
        self.calls.append(("updateUserPermissions", kwargs))
        permissions = kwargs["permissions"]
        return Ok({"permissions": permissions})


class FakeAdminService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def getAdminInfo(self, admin_info):
        self.calls.append(("getAdminInfo", admin_info))
        return {"user_id": admin_info["id"], "username": admin_info["username"], "email": admin_info["email"]}

    async def getDashboardSummary(self):
        self.calls.append(("getDashboardSummary", None))
        return {"organizations": 1, "projects": 2, "api_keys": 3, "users": 4}

    def listOrganizationPermissions(self):
        return {"permissions": ["organization.owner"]}

    def listProjectPermissions(self):
        return {"permissions": ["project.owner"]}

    def listApiKeyPermissions(self):
        return {"total": 1, "results": [{"id": "chat.read", "name": "Chat Read", "description": "Read chat"}]}

    async def listOrganizations(self, pagination):
        self.calls.append(("listOrganizations", pagination))
        return {"total": 1, "results": [org_payload()]}

    async def createOrganization(self, input_data):
        self.calls.append(("createOrganization", input_data))
        return org_payload("org-created")

    async def getOrganization(self, org_id: str):
        self.calls.append(("getOrganization", org_id))
        return org_payload(org_id)

    async def updateOrganization(self, org_id: str, input_data):
        self.calls.append(("updateOrganization", {"org_id": org_id, "input_data": input_data}))
        payload = org_payload(org_id)
        payload["name"] = input_data.name
        return payload

    async def deleteOrganization(self, org_id: str):
        self.calls.append(("deleteOrganization", org_id))
        return {
            "id": org_id,
            "requested_at": "2026-01-01T00:00:00",
            "cancel_before": "2026-01-31T00:00:00",
        }

    async def getOrganizationSettings(self, org_id: str):
        self.calls.append(("getOrganizationSettings", org_id))
        return {"rate_limit": 100, "spending_limit": 1000, "extra": {"tier": "pro"}}

    async def updateOrganizationSettings(self, org_id: str, input_data):
        self.calls.append(("updateOrganizationSettings", {"org_id": org_id, "input_data": input_data}))
        return {
            "rate_limit": input_data.rate_limit,
            "spending_limit": input_data.spending_limit,
            "extra": input_data.extra,
        }

    async def listOrganizationUsers(self, org_id: str, pagination):
        self.calls.append(("listOrganizationUsers", {"org_id": org_id, "pagination": pagination}))
        return {"total": 1, "results": [{"id": "user-1", "username": "alice", "email": "alice@example.com"}]}

    async def listProjects(self, org_id: str, pagination):
        self.calls.append(
            (
                "listProjects",
                {"org_id": org_id, "pagination": pagination},
            )
        )
        return {"total": 1, "results": [project_payload()]}

    async def createProject(self, org_id: str, input_data):
        self.calls.append(("createProject", {"org_id": org_id, "input_data": input_data}))
        return project_payload()

    async def getProject(self, project_id: str):
        self.calls.append(("getProject", project_id))
        return project_payload(project_id)

    async def updateProject(self, project_id: str, input_data):
        self.calls.append(("updateProject", {"project_id": project_id, "input_data": input_data}))
        payload = project_payload(project_id)
        payload["name"] = input_data.name
        payload["description"] = input_data.description
        return payload

    async def deleteProject(self, project_id: str):
        self.calls.append(("deleteProject", project_id))
        return {"id": project_id, "archived": True}

    async def archiveProject(self, project_id: str):
        self.calls.append(("archiveProject", project_id))
        return {"id": project_id, "archived": True}

    async def unarchiveProject(self, project_id: str):
        self.calls.append(("unarchiveProject", project_id))
        return {"id": project_id, "archived": False}

    async def getProjectSettings(self, project_id: str):
        self.calls.append(("getProjectSettings", project_id))
        return {"rate_limit": 120, "spending_limit": 5000, "extra": {"mode": "burst"}}

    async def updateProjectSettings(self, project_id: str, input_data):
        self.calls.append(("updateProjectSettings", {"project_id": project_id, "input_data": input_data}))
        return {
            "rate_limit": input_data.rate_limit,
            "spending_limit": input_data.spending_limit,
            "extra": input_data.extra,
        }

    async def listProjectUsers(self, project_id: str, pagination):
        self.calls.append(("listProjectUsers", {"project_id": project_id, "pagination": pagination}))
        return {"total": 1, "results": [{"id": "user-2", "username": "bob", "email": "bob@example.com"}]}

    async def listApiKeys(self, project_id: str, disabled: bool | None = None):
        self.calls.append(
            (
                "listApiKeys",
                {"project_id": project_id, "disabled": disabled},
            )
        )
        payload = api_key_payload(project_uuid=project_id)
        if disabled is not None:
            payload["disabled"] = disabled
        return {"total": 1, "results": [payload]}

    async def createApiKey(self, user_info, project_id: str, input_data):
        self.calls.append(("createApiKey", {"user_info": user_info, "project_id": project_id, "input_data": input_data}))
        payload = api_key_payload(project_uuid=project_id)
        payload["key"] = "sk_api-key-1.secret"
        return payload

    async def getApiKey(
        self,
        api_key_uuid: str,
        disabled: bool | None = None,
    ):
        self.calls.append(
            (
                "getApiKey",
                {"api_key_uuid": api_key_uuid, "disabled": disabled},
            )
        )
        payload = api_key_payload(api_key_uuid=api_key_uuid)
        if disabled is not None:
            payload["disabled"] = disabled
        return payload

    async def updateApiKey(self, api_key_uuid: str, input_data):
        self.calls.append(("updateApiKey", {"api_key_uuid": api_key_uuid, "input_data": input_data}))
        payload = api_key_payload(api_key_uuid=api_key_uuid)
        payload["name"] = input_data.name
        payload["description"] = input_data.description
        payload["permissions"] = input_data.permissions
        if getattr(input_data, "disabled", None) is not None:
            payload["disabled"] = input_data.disabled
        return payload

    async def deleteApiKey(self, api_key_uuid: str):
        self.calls.append(("deleteApiKey", api_key_uuid))
        return None

    async def listUsers(self, pagination):
        self.calls.append(("listUsers", pagination))
        self.pagination = pagination
        return {"total": 1, "results": [{"user_id": "user-1", "username": "alice", "email": "alice@example.com", "first_name": "Alice", "last_name": "Example", "enabled": True, "email_verified": True}]}

    async def getUserOrganizations(self, user_id: str):
        self.calls.append(("getUserOrganizations", user_id))
        return [{"org_id": "org-1", "name": "Org 1", "alias": "org-1"}]

    async def getUserProfile(self, user_id: str):
        self.calls.append(("getUserProfile", user_id))
        return {
            "user_id": user_id,
            "username": "alice",
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Example",
            "enabled": True,
            "email_verified": True,
            "organizations": [{"org_id": "org-1", "name": "Org 1", "alias": "org-1"}],
            "permissions": {"organization_permissions": [], "effective_organization_permissions": [], "project_permissions": []},
        }

    async def getUserPermissions(self, user_id: str):
        self.calls.append(("getUserPermissions", user_id))
        return {
            "organization_permissions": ["organization.settings.read"],
            "effective_organization_permissions": [
                "organization.settings.read"
            ],
            "project_permissions": [
                {
                    "project_uuid": PROJECT_UUID,
                    "permissions": ["project.settings.read"],
                    "effective_permissions": ["project.settings.read"],
                }
            ],
        }

    async def setUserPermissions(self, user_id: str, input_data):
        self.calls.append(("setUserPermissions", {"user_id": user_id, "input_data": input_data}))
        return self._profile(
            user_id,
            {
                "organization_permissions": input_data.organization_permissions,
                "effective_organization_permissions": input_data.organization_permissions,
                "project_permissions": [
                    {
                        "project_uuid": item.project_uuid,
                        "permissions": item.permissions,
                        "effective_permissions": item.permissions,
                    }
                    for item in input_data.project_permissions
                ],
            },
        )

    async def setUserOrganizationPermissions(
        self,
        user_id: str,
        org_id: str,
        permissions: list[str],
    ):
        self.calls.append(
            (
                "setUserOrganizationPermissions",
                {
                    "user_id": user_id,
                    "org_id": org_id,
                    "permissions": permissions,
                },
            )
        )
        return self._profile(
            user_id,
            {
                "organization_permissions": permissions,
                "effective_organization_permissions": permissions,
                "project_permissions": [
                    {
                        "project_uuid": PROJECT_UUID,
                        "permissions": ["project.settings.read"],
                        "effective_permissions": ["project.settings.read"],
                    }
                ],
            },
        )

    async def setUserProjectPermissions(
        self,
        user_id: str,
        project_id: str,
        permissions: list[str],
    ):
        self.calls.append(
            (
                "setUserProjectPermissions",
                {
                    "user_id": user_id,
                    "project_id": project_id,
                    "permissions": permissions,
                },
            )
        )
        return self._profile(
            user_id,
            {
                "organization_permissions": ["organization.settings.read"],
                "effective_organization_permissions": [
                    "organization.settings.read"
                ],
                "project_permissions": [
                    {
                        "project_uuid": project_id,
                        "permissions": permissions,
                        "effective_permissions": permissions,
                    }
                ],
            },
        )

    async def resetUserPermissions(self, user_id: str):
        self.calls.append(("resetUserPermissions", user_id))
        return self._profile(
            user_id,
            {
                "organization_permissions": [],
                "effective_organization_permissions": [],
                "project_permissions": [],
            },
        )

    def _profile(self, user_id: str, permissions: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "username": "alice",
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Example",
            "enabled": True,
            "email_verified": True,
            "organizations": [
                {"org_id": "org-1", "name": "Org 1", "alias": "org-1"}
            ],
            "permissions": permissions,
        }


# Cross-app API fakes -------------------------------------------------------

import uuid
from decimal import Decimal

FILE_UUID = "22222222-2222-2222-2222-222222222222"
CONVERSATION_UUID = "33333333-3333-3333-3333-333333333333"
TRANSACTION_UUID = "44444444-4444-4444-4444-444444444444"
INVOICE_UUID = "55555555-5555-5555-5555-555555555555"
BILLING_SOURCE_UUID = "66666666-6666-6666-6666-666666666666"


def api_key_info_payload() -> dict[str, Any]:
    return ApiKeyInfoFactory()


def file_info_payload() -> dict[str, Any]:
    return {
        "uid": uuid.UUID(FILE_UUID),
        "filename": "report.txt",
        "mime_type": "text/plain",
        "size": 12,
        "created_at": NOW,
        "extra_metadata": {"kind": "report"},
    }


def rag_result_payload() -> dict[str, Any]:
    return {
        "file_info": file_info_payload(),
        "text": "matched text",
        "embedding": [0.1, 0.2],
        "created_at": NOW,
    }


def transaction_payload():
    from gantry.management.billing.dtos import TransactionInfoResponse

    return TransactionInfoResponse(
        transaction_uid=uuid.UUID(TRANSACTION_UUID),
        amount=Decimal("12.34"),
        date=NOW,
        project_uuid=uuid.UUID(PROJECT_UUID),
        details={"model": "gpt"},
        captured_at=None,
        status=TransactionStatus.PENDING,
    )


def invoice_payload(detail: bool = False) -> dict[str, Any]:
    payload = {
        "invoice_uid": uuid.UUID(INVOICE_UUID),
        "billing_period": NOW.date(),
        "total_amount": Decimal("20.00"),
        "paid_at": None,
        "details": {"period": "monthly"},
        "used_credits": Decimal("1.00"),
    }
    if detail:
        payload["line_items"] = [
            {
                "description": "usage",
                "amount": Decimal("20.00"),
                "project_uuid": uuid.UUID(PROJECT_UUID),
                "project_name": "Project 1",
            }
        ]
    return payload


def billing_source_payload(detail: bool = False) -> dict[str, Any]:
    payload = {
        "billing_source_uid": uuid.UUID(BILLING_SOURCE_UUID),
        "organization_id": "org-1",
        "source_type": "stripe",
        "created_at": NOW,
    }
    if detail:
        payload.update(
            {
                "provider_id": "cus_123",
                "email": "billing@example.com",
                "phone": "+10000000000",
                "name": "Billing User",
                "default_payment_method": None,
                "billing_address": {
                    "line1": "1 Main",
                    "line2": "Suite 1",
                    "city": "HCM",
                    "state": "HCM",
                    "postal_code": "70000",
                    "country": "VN",
                },
            }
        )
    return payload


class FakeBillingAggregateQueryService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def get_aggregate_by_projects(self, **kwargs):
        self.calls.append(("get_aggregate_by_projects", kwargs))
        return Ok([
            {
                "period_bucket": NOW,
                "transaction_count": 2,
                "total_amount": Decimal("12.34"),
            }
        ])

    async def getAggregateByProjects(self, **kwargs):
        self.calls.append(("getAggregateByProjects", kwargs))
        return Ok([
            {
                "period_bucket": NOW,
                "transaction_count": 2,
                "total_amount": Decimal("12.34"),
            }
        ])

    async def getAggregateByProjectsForAdmin(self, **kwargs):
        self.calls.append(("getAggregateByProjectsForAdmin", kwargs))
        return Ok([
            {
                "period_bucket": NOW,
                "transaction_count": 3,
                "total_amount": Decimal("33.33"),
            }
        ])

    async def get_aggregate_by_org(self, **kwargs):
        self.calls.append(("get_aggregate_by_org", kwargs))
        return Ok([
            {
                "period_bucket": NOW,
                "transaction_count": 5,
                "total_amount": Decimal("99.99"),
            }
        ])

    async def getAggregateByOrg(self, **kwargs):
        self.calls.append(("getAggregateByOrg", kwargs))
        return Ok([
            {
                "period_bucket": NOW,
                "transaction_count": 5,
                "total_amount": Decimal("99.99"),
            }
        ])


class FakeBillingSourceService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def createBillingSource(self, **kwargs):
        self.calls.append(("createBillingSource", kwargs))
        return Ok(billing_source_payload())

    async def getBillingSource(self, org_id: str):
        self.calls.append(("getBillingSource", org_id))
        return Ok(billing_source_payload(detail=True))

    async def updateBillingSource(self, **kwargs):
        self.calls.append(("updateBillingSource", kwargs))
        return Ok(True)

    async def createSetupIntent(self, org_id: str):
        self.calls.append(("createSetupIntent", org_id))
        return Ok({"client_secret": "seti_secret"})

    async def deletePaymentMethod(self, org_id: str, payment_method_id: str):
        self.calls.append(("deletePaymentMethod", {"org_id": org_id, "payment_method_id": payment_method_id}))
        return Ok(True)

    async def listPaymentMethods(self, org_id: str):
        self.calls.append(("listPaymentMethods", org_id))
        return Ok([{"id": "pm_123", "type": "card"}])

    async def getPaymentMethodDetails(self, org_id: str, payment_method_id: str):
        self.calls.append(("getPaymentMethodDetails", {"org_id": org_id, "payment_method_id": payment_method_id}))
        return Ok({"id": payment_method_id, "type": "card"})

    async def listRequiredActionSetupIntents(self, org_id: str):
        self.calls.append(("listRequiredActionSetupIntents", org_id))
        return Ok([{"id": "seti_123", "status": "requires_action"}])

    async def cancelSetupIntent(self, org_id: str, setup_intent_id: str):
        self.calls.append(("cancelSetupIntent", {"org_id": org_id, "setup_intent_id": setup_intent_id}))
        return Ok(True)


class FakeCreditService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def getAvailableCredits(self, org_id: str):
        self.calls.append(("getAvailableCredits", org_id))
        return Decimal("42.00")

    async def getCreditTransactions(self, **kwargs):
        self.calls.append(("getCreditTransactions", kwargs))
        return ([{"amount": Decimal("5.00"), "description": "promo", "created_at": NOW}], 1)

    async def addCredits(self, **kwargs):
        self.calls.append(("addCredits", kwargs))
        return Decimal("47.00")


class FakeInvoiceService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def listInvoices(self, **kwargs):
        self.calls.append(("listInvoices", kwargs))
        return Ok(([invoice_payload()], 1))

    async def listInvoicesForAdmin(self, **kwargs):
        self.calls.append(("listInvoicesForAdmin", kwargs))
        return Ok(([invoice_payload()], 1))

    async def getInvoiceById(self, **kwargs):
        self.calls.append(("getInvoiceById", kwargs))
        return Ok(invoice_payload(detail=True))

    async def getInvoiceByIdForAdmin(self, **kwargs):
        self.calls.append(("getInvoiceByIdForAdmin", kwargs))
        return Ok(invoice_payload(detail=True))

    async def getInvoiceByIdPaymentLinkInProvider(self, **kwargs):
        self.calls.append(("getInvoiceByIdPaymentLinkInProvider", kwargs))
        return Ok("https://billing.example/pay")

    async def markInvoiceAsPaidManually(self, **kwargs):
        self.calls.append(("markInvoiceAsPaidManually", kwargs))
        return Ok(True)

    async def markInvoiceAsRefundedManually(self, **kwargs):
        self.calls.append(("markInvoiceAsRefundedManually", kwargs))
        return Ok(True)

    async def markInvoiceAsPaid(self, *args, **kwargs):
        self.calls.append(("markInvoiceAsPaid", {"args": args, "kwargs": kwargs}))
        return Ok(True)


class FakeBillingTransactionService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def getTransactions(self, **kwargs):
        self.calls.append(("getTransactions", kwargs))
        return ([transaction_payload()], 1)

    async def getTransactionById(self, **kwargs):
        self.calls.append(("getTransactionById", kwargs))
        return Ok(transaction_payload())

    async def getTransactionsForAdmin(self, **kwargs):
        self.calls.append(("getTransactionsForAdmin", kwargs))
        return ([transaction_payload()], 1)

    async def getTransactionByIdForAdmin(self, **kwargs):
        self.calls.append(("getTransactionByIdForAdmin", kwargs))
        return Ok(transaction_payload())

    async def post(self, **kwargs):
        self.calls.append(("post", kwargs))
        return Ok(uuid.UUID(TRANSACTION_UUID))

    async def capture(self, **kwargs):
        self.calls.append(("capture", kwargs))
        return Ok(True)


class FakeLogQueryService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def search_logs(self, *args):
        self.calls.append(("search_logs", args))
        return Ok([{"timestamp": NOW.isoformat(), "message": "ok"}])


class FakeFileStorageService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def uploadFile(self, *args):
        self.calls.append(("uploadFile", args))
        return uuid.UUID(FILE_UUID)

    async def uploadFileByProjectUUID(self, *args):
        self.calls.append(("uploadFileByProjectUUID", args))
        return uuid.UUID(FILE_UUID)

    async def listFilesInProject(self, project_id: int):
        self.calls.append(("listFilesInProject", project_id))
        return [file_info_payload()]

    async def listFilesInProjectByUUID(self, project_uuid: str):
        self.calls.append(("listFilesInProjectByUUID", project_uuid))
        return [file_info_payload()]

    async def getFileUrl(self, file_id, project_id):
        self.calls.append(("getFileUrl", {"file_id": file_id, "project_id": project_id}))
        return Ok("https://files.example/download")

    async def getFileUrlByProjectUUID(self, file_id, project_uuid):
        self.calls.append(("getFileUrlByProjectUUID", {"file_id": file_id, "project_uuid": project_uuid}))
        return Ok("https://files.example/download")

    async def getFileInfoAndUrl(self, file_id, project_id):
        self.calls.append(("getFileInfoAndUrl", {"file_id": file_id, "project_id": project_id}))
        return Ok(("https://files.example/download", file_info_payload()))

    async def getFileInfoAndUrlByProjectUUID(self, file_id, project_uuid):
        self.calls.append(("getFileInfoAndUrlByProjectUUID", {"file_id": file_id, "project_uuid": project_uuid}))
        return Ok(("https://files.example/download", file_info_payload()))

    async def getFileInfo(self, file_id, project_id):
        self.calls.append(("getFileInfo", {"file_id": file_id, "project_id": project_id}))
        return Ok(file_info_payload())

    async def getFileInfoByProjectUUID(self, file_id, project_uuid):
        self.calls.append(("getFileInfoByProjectUUID", {"file_id": file_id, "project_uuid": project_uuid}))
        return Ok(file_info_payload())

    async def deleteFile(self, file_id, project_id):
        self.calls.append(("deleteFile", {"file_id": file_id, "project_id": project_id}))
        return Ok(True)

    async def deleteFileByProjectUUID(self, file_id, project_uuid):
        self.calls.append(("deleteFileByProjectUUID", {"file_id": file_id, "project_uuid": project_uuid}))
        return Ok(True)

    async def updateFileMetadata(self, file_id, project_id, extra_metadata):
        self.calls.append(("updateFileMetadata", {"file_id": file_id, "project_id": project_id, "extra_metadata": extra_metadata}))
        return Ok(True)

    async def updateFileMetadataByProjectUUID(self, file_id, project_uuid, extra_metadata):
        self.calls.append(("updateFileMetadataByProjectUUID", {"file_id": file_id, "project_uuid": project_uuid, "extra_metadata": extra_metadata}))
        return Ok(True)


class FakeRagService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def getSupportedLanguages(self):
        self.calls.append(("getSupportedLanguages", None))
        return ["english", "simple"]

    async def addEmbedding(self, *args):
        self.calls.append(("addEmbedding", args))
        return Ok(True)

    async def getFilesInRag(self, project_id: int):
        self.calls.append(("getFilesInRag", project_id))
        return [file_info_payload()]

    async def getFilesInRagByProjectUid(self, project_uuid: str):
        self.calls.append(("getFilesInRagByProjectUid", project_uuid))
        return [file_info_payload()]

    async def addFile(self, *args):
        self.calls.append(("addFile", args))
        return Ok("task-1")

    async def addFileByProjectUid(self, *args):
        self.calls.append(("addFileByProjectUid", args))
        return Ok("task-1")

    async def getTaskStatus(self, task_id: str, project_id: int):
        self.calls.append(("getTaskStatus", {"task_id": task_id, "project_id": project_id}))
        return Ok({"task_id": task_id, "type": "file", "text": None, "metadata": None, "file_uid": uuid.UUID(FILE_UUID), "project_uuid": uuid.UUID(PROJECT_UUID), "chunk_splitter": "recursive", "chunk_splitter_options": {}, "chunk_size": 1000, "chunk_overlap": 150, "status": "completed"})

    async def getTaskStatusByProjectUid(self, task_id: str, project_uuid: str):
        self.calls.append(("getTaskStatusByProjectUid", {"task_id": task_id, "project_uuid": project_uuid}))
        return Ok({"task_id": task_id, "type": "file", "text": None, "metadata": None, "file_uid": uuid.UUID(FILE_UUID), "project_uuid": project_uuid, "chunk_splitter": "recursive", "chunk_splitter_options": {}, "chunk_size": 1000, "chunk_overlap": 150, "status": "completed"})

    async def querySimilarByVector(self, *args):
        self.calls.append(("querySimilarByVector", args))
        return Ok([rag_result_payload()])

    async def querySimilarByText(self, *args):
        self.calls.append(("querySimilarByText", args))
        return Ok([rag_result_payload()])

    async def querySimilarByTextByProjectUid(self, *args):
        self.calls.append(("querySimilarByTextByProjectUid", args))
        return Ok([rag_result_payload()])


class BaseConversationService(ConfigurableFake):
    """Base fake conversation service with common core methods."""
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def getConversationMetadata(self, conversation_uid, project_id):
        self.calls.append(("getConversationMetadata", {"conversation_uid": conversation_uid, "project_id": project_id}))
        return Ok({"conversation_id": 1, "conversation_uid": conversation_uid, "project_id": project_id, "extra_metadata": {"topic": "demo"}, "created_at": NOW, "tree_structure": None, "active_leaf_message_id": None, "conversation_type": ConversationType.SEQUENCE, "relationships_map": None})

    async def getConversationMessageByUuid(self, conversation_uid, project_id, message_uid):
        self.calls.append(("getConversationMessageByUuid", {"conversation_uid": conversation_uid, "project_id": project_id, "message_uid": message_uid}))
        return Ok(SimpleNamespace(uuid=message_uid, payload={"role": "user", "content": "hello"}, timestamp=NOW, run_id=None, extra_metadata=None))

    async def getConversationMessagesByUuids(self, conversation_uid, project_id, message_uids):
        self.calls.append(("getConversationMessagesByUuids", {"conversation_uid": conversation_uid, "project_id": project_id, "message_uids": message_uids}))
        return [SimpleNamespace(uuid=uid, payload={"role": "user", "content": f"message-{i}"}, timestamp=NOW, run_id=None, extra_metadata=None) for i, uid in enumerate(message_uids)]

    async def updateConversationMetadata(self, conversation_uid, project_id, extra_metadata):
        self.calls.append(("updateConversationMetadata", {"conversation_uid": conversation_uid, "project_id": project_id, "extra_metadata": extra_metadata}))
        return Ok(None)

    async def deleteConversation(self, conversation_uid, project_id):
        self.calls.append(("deleteConversation", {"conversation_uid": conversation_uid, "project_id": project_id}))
        return Ok(None)

    async def deleteConversationMessage(self, conversation_uid, project_id, message_uid):
        self.calls.append(("deleteConversationMessage", {"conversation_uid": conversation_uid, "project_id": project_id, "message_uid": message_uid}))
        return Ok(None)

    async def addConversationMessagesCache(self, conversation_uid, msgs):
        self.calls.append(("addConversationMessagesCache", {"conversation_uid": conversation_uid, "msg_count": len(msgs)}))
        return None


class FakeSequenceConversationService(BaseConversationService):
    """Fake implementation of SequenceConversationService with sequence-specific methods."""

    async def createConversation(self, project_id, extra_metadata, messages=None):
        self.calls.append(("createConversation", {"project_id": project_id, "extra_metadata": extra_metadata, "msg_count": len(messages) if messages else 0}))
        return Ok(uuid.UUID(CONVERSATION_UUID))

    async def getConversationMessages(self, conversation_uid, project_id, limit=20, last_cursor=None, order_by="asc"):
        self.calls.append(("getConversationMessages", {"conversation_uid": conversation_uid, "project_id": project_id, "limit": limit, "last_cursor": last_cursor, "order_by": order_by}))
        return Ok([SimpleNamespace(uuid=uuid.uuid4(), payload={"role": "user", "content": f"message-{i}"}, timestamp=NOW, run_id=None, extra_metadata=None) for i in range(min(limit, 5))])

    async def storeConversationMessages(self, conversation_uid, project_id, msgs):
        self.calls.append(("storeConversationMessages", {"conversation_uid": conversation_uid, "project_id": project_id, "msg_count": len(msgs)}))
        return Ok(None)


class FakeTreeConversationService(BaseConversationService):
    """Fake implementation of TreeConversationService with tree-specific methods."""

    async def createConversation(self, project_id, extra_metadata, messages=None):
        self.calls.append(("createConversation", {"project_id": project_id, "extra_metadata": extra_metadata, "msg_count": len(messages) if messages else 0}))
        return Ok(uuid.UUID(CONVERSATION_UUID))

    async def getConversationMessages(self, conversation_uid, project_id, limit=20, order_by="asc", last_cursor=None, branch_node_id=None):
        self.calls.append(("getConversationMessages", {"conversation_uid": conversation_uid, "project_id": project_id, "limit": limit, "order_by": order_by, "last_cursor": last_cursor, "branch_node_id": branch_node_id}))
        return Ok([SimpleNamespace(uuid=uuid.uuid4(), payload={"role": "user", "content": f"message-{i}"}, timestamp=NOW, run_id=None, extra_metadata=None) for i in range(min(limit, 5))])

    async def storeConversationMessages(self, conversation_uid, project_id, msgs):
        self.calls.append(("storeConversationMessages", {"conversation_uid": conversation_uid, "project_id": project_id, "msg_count": len(msgs)}))
        return Ok(None)


# Legacy alias for backward compatibility
FakeConversationService = FakeSequenceConversationService


class FakeGatewayDestination(SimpleNamespace):
    pass


class FakeGatewayService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.destination = FakeGatewayDestination(address="https://upstream.example/base/", permission="chat.read")

    def getDestination(self, route_name: str):
        self.calls.append(("getDestination", route_name))
        return Ok(self.destination)

    def checkPermission(self, permissions, destination):
        self.calls.append(("checkPermission", {"permissions": permissions, "destination": destination}))
        return Ok(True)


class FakeAiGatewayService(ConfigurableFake):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def getModels(self) -> list[str]:
        self.calls.append(("getModels", None))
        return ["gpt-test"]

    async def route(self, model, project_id, run_input, model_settings):
        self.calls.append(("route", {"model": model, "project_id": project_id}))

        async def _events():
            if False:
                yield ""

        return Ok(_events())
