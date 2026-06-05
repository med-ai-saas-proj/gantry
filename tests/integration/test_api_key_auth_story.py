from __future__ import annotations

import pytest
from pyrusult import ResultStatus

pytestmark = pytest.mark.integration


async def _create_project_for_api_key_story(org_id: str):
    from gantry.db.factories import getSessionManager
    from gantry.management.organization.factories import getOrgSettingsRepository
    from gantry.management.project.factories import (
        getProjectRepository,
        getProjectSettingsRepository,
    )

    session_manager = getSessionManager()
    project_repo = getProjectRepository()
    org_settings_repo = getOrgSettingsRepository()
    project_settings_repo = getProjectSettingsRepository()
    async with session_manager.get_session() as session:
        await org_settings_repo.upsert(
            session,
            org_id=org_id,
            rate_limit=120,
            spending_limit=100,
            extra={"tier": "integration"},
        )
        project = await project_repo.create(
            session,
            name="Integration API Key Project",
            description="Project for real API key auth integration tests",
            organization_id=org_id,
        )
        await project_settings_repo.upsert(
            session,
            project_id=project.id,
            rate_limit=60,
            spending_limit=50,
            extra={"source": "integration"},
        )
        await session.commit()
        return project.id, str(project.uuid)


@pytest.mark.asyncio
async def test_api_key_create_parse_and_verify_uses_real_storage_and_cache(
    migrated_management_storage,
    integration_stack,
) -> None:
    from gantry.management.api_key.factories import getApiKeyService

    assert integration_stack.timescale_asyncpg_uri
    assert integration_stack.redis_url
    org_id = "integration-api-key-org"
    project_id, project_uuid = await _create_project_for_api_key_story(org_id)
    service = getApiKeyService()

    created_res = await service.createApiKey(
        actor_user_id="gantry-test-user",
        project_uuid=project_uuid,
        name="integration key",
        description="created in integration suite",
        permissions=["chat.read", "conversation.read"],
    )

    assert created_res.status == ResultStatus.Ok
    created = created_res.unwrap()
    assert created.api_key_uuid
    assert created.project_uuid == project_uuid
    assert created.key.startswith("sk_")

    parsed_res = await service.parseApiKey(created.key)
    verified_res = await service.verifyApiKey(created.key, ["chat.read"])

    assert parsed_res.status == ResultStatus.Ok
    parsed = parsed_res.unwrap()
    assert parsed["api_key_id"] > 0
    assert parsed["api_key_uuid"] == created.api_key_uuid
    assert parsed["project_id"] == project_id
    assert parsed["project_uuid"] == project_uuid
    assert parsed["organization_uuid"] == org_id
    assert parsed["hashed_key"]
    assert set(parsed["permissions"]) == {"chat.read", "conversation.read"}
    assert parsed["rpm_limit_organization"] == 120
    assert parsed["rpm_limit_project"] == 60
    assert parsed["spending_limit_organization"] == 100
    assert parsed["spending_limit_project"] == 50
    assert verified_res.status == ResultStatus.Ok


@pytest.mark.asyncio
async def test_api_key_auth_rejects_invalid_missing_permission_and_disabled_keys(
    migrated_management_storage,
    integration_stack,
) -> None:
    from gantry.management.api_key.factories import getApiKeyService

    assert integration_stack.timescale_asyncpg_uri
    assert integration_stack.redis_url
    _, project_uuid = await _create_project_for_api_key_story(
        "integration-api-key-negative-org"
    )
    service = getApiKeyService()
    created_res = await service.createApiKey(
        actor_user_id="gantry-test-user",
        project_uuid=project_uuid,
        name="negative key",
        description="negative auth scenarios",
        permissions=["chat.read"],
    )
    created = created_res.unwrap()

    invalid_res = await service.parseApiKey("not-a-valid-key")
    missing_permission_res = await service.verifyApiKey(
        created.key,
        ["chat.run"],
    )

    assert invalid_res.status == ResultStatus.Err
    assert missing_permission_res.status == ResultStatus.Err

    disabled_created = (
        await service.createApiKey(
            actor_user_id="gantry-test-user",
            project_uuid=project_uuid,
            name="disabled key",
            description="disabled auth scenario",
            permissions=["chat.read"],
        )
    ).unwrap()
    disabled_res = await service.setApiKeyDisabled(
        api_key_uuid=disabled_created.api_key_uuid,
        disabled=True,
    )
    disabled_parse_res = await service.parseApiKey(disabled_created.key)

    assert disabled_res.status == ResultStatus.Ok
    assert disabled_parse_res.status == ResultStatus.Err
