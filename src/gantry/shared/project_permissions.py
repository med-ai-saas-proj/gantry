"""Shared helpers for grouped project-permission attribute payloads."""

import json
from typing import Any


type ProjectPermissionMap = dict[str, list[str]]


def _dedupe_permissions(values: Any) -> list[str]:
    """Normalize one permission list into distinct non-empty strings."""
    if not isinstance(values, list):
        return []

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def normalize_project_permission_map(raw: Any) -> ProjectPermissionMap:
    """Normalize project permissions from the grouped map format only."""
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {}
        return normalize_project_permission_map(parsed)

    if isinstance(raw, list):
        normalized: ProjectPermissionMap = {}
        for value in raw:
            parsed = normalize_project_permission_map(value)
            for project_uuid, permissions in parsed.items():
                merged = normalized.setdefault(project_uuid, [])
                seen = set(merged)
                for permission in permissions:
                    if permission in seen:
                        continue
                    seen.add(permission)
                    merged.append(permission)
        return normalized

    if not isinstance(raw, dict):
        return {}

    normalized: ProjectPermissionMap = {}
    for project_uuid, permissions in raw.items():
        if not isinstance(project_uuid, str) or not project_uuid:
            continue
        deduped = _dedupe_permissions(permissions)
        if deduped:
            normalized[project_uuid] = deduped
    return normalized


def serialize_project_permission_map(
    permissions_by_project: ProjectPermissionMap,
) -> ProjectPermissionMap:
    """Return a normalized grouped permission map for persistence."""
    return normalize_project_permission_map(permissions_by_project)


def serialize_project_permission_values(
    permissions_by_project: ProjectPermissionMap,
) -> list[str]:
    """Encode one project permission map into Keycloak multivalue strings."""
    normalized = normalize_project_permission_map(permissions_by_project)
    return [
        json.dumps(
            {project_uuid: permissions},
            separators=(",", ":"),
            sort_keys=True,
        )
        for project_uuid, permissions in normalized.items()
    ]
