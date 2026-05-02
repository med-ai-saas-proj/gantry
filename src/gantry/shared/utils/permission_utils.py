"""Shared helpers for grouped project-permission attribute payloads."""

import json
from typing import Any


type ProjectPermissionMap = dict[str, list[str]]


def _dedupe_permissions(values: Any) -> list[str]:
    """Normalize one permission list into distinct non-empty strings."""
    if not isinstance(values, list):
        return []

    deduped: list[str] = []
    _append_unique_permissions(deduped, values)
    return deduped


def _append_unique_permissions(target: list[str], values: list[Any]) -> None:
    """Append distinct non-empty string permissions without changing existing order."""
    seen = set(target)
    for permission in values:
        if not isinstance(permission, str) or not permission:
            continue
        if permission in seen:
            continue
        seen.add(permission)
        target.append(permission)


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
                _append_unique_permissions(merged, permissions)
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
