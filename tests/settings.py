"""Shared settings for test suites."""

from __future__ import annotations

from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
DEFAULT_CONFIG_FILE = REPO_ROOT / "gantry.toml"
EXAMPLE_CONFIG_FILE = REPO_ROOT / "example.gantry.toml"

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
MAILPIT_API_URL = os.environ.get("MAILPIT_API_URL", "http://localhost:8025")
REALM = os.environ.get("REALM", "gantry")


def config_file() -> Path:
    configured = os.environ.get("GANTRY_SERVER__CONFIG_FILE")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else REPO_ROOT / path
    if DEFAULT_CONFIG_FILE.exists():
        return DEFAULT_CONFIG_FILE
    return EXAMPLE_CONFIG_FILE
