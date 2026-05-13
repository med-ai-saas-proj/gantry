"""Regenerate committed regression snapshots from the current FastAPI apps.

Run from repository root:
    PYTHONPATH=src:. GANTRY_SERVER__CONFIG_FILE=gantry.toml \
      uv run --group dev python tests/snapshots/update_snapshots.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_ROOT))
os.environ.setdefault("GANTRY_SERVER__CONFIG_FILE", str(REPO_ROOT / "gantry.toml"))

from tests.helpers.routes import operation_lines
from tests.regression.helpers import operation_contracts, selected_schemas
from tests.regression.test_response_snapshots import (
    GATEWAY_SCHEMAS,
    INTERNAL_SCHEMAS,
    MANAGEMENT_SCHEMAS,
    SERVICE_SCHEMAS,
)

SNAPSHOT_DIR = Path(__file__).resolve().parent


def _write_text(name: str, content: str) -> None:
    (SNAPSHOT_DIR / name).write_text(content)


def _write_json(name: str, payload: object) -> None:
    _write_text(name, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _openapi_docs() -> dict[str, dict]:
    from gantry.api_gateway.routes import gateway_app
    from gantry.main.app import internal_app
    from gantry.management import management_app
    from gantry.service import service_app

    return {
        "management": management_app.openapi(),
        "service": service_app.openapi(),
        "gateway": gateway_app.openapi(),
        "internal": internal_app.openapi(),
    }


def main() -> None:
    openapi = _openapi_docs()

    for app_name, spec in openapi.items():
        _write_text(
            f"{app_name}_operations.tsv",
            "\n".join(operation_lines(spec)) + "\n",
        )
        _write_json(
            f"{app_name}_operation_contracts.json",
            operation_contracts(spec),
        )

    _write_text(
        "management_paths.txt",
        "\n".join(sorted(openapi["management"]["paths"])) + "\n",
    )
    _write_json(
        "selected_response_schemas.json",
        selected_schemas(openapi["management"], MANAGEMENT_SCHEMAS),
    )
    _write_json(
        "selected_service_response_schemas.json",
        selected_schemas(openapi["service"], SERVICE_SCHEMAS),
    )
    _write_json(
        "selected_internal_response_schemas.json",
        selected_schemas(openapi["internal"], INTERNAL_SCHEMAS),
    )
    _write_json(
        "gateway_proxy_contract.json",
        selected_schemas(openapi["gateway"], GATEWAY_SCHEMAS),
    )

    from gantry.management.api_key.settings import getApiKeysSettings
    from gantry.management.organization.permissions import (
        ALL_PERMISSIONS as ORGANIZATION_PERMISSIONS,
    )
    from gantry.management.project.permissions import (
        ALL_PERMISSIONS as PROJECT_PERMISSIONS,
    )

    _write_json(
        "permission_catalogs.json",
        {
            "api_key": [
                permission.id for permission in getApiKeysSettings().permissions
            ],
            "organization": list(ORGANIZATION_PERMISSIONS),
            "project": list(PROJECT_PERMISSIONS),
        },
    )

    print(f"Updated snapshots in {SNAPSHOT_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
