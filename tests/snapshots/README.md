# Regression Snapshots

These files are generated from the current FastAPI OpenAPI documents and permission catalogs.
They are used by `tests/regression` to detect public API drift.

## Check Snapshots

```bash
PYTHONPATH=src GANTRY_SERVER__CONFIG_FILE=gantry.toml \
  uv run --group dev pytest tests/regression -m regression -q
```

## Regenerate Snapshots

Run this only when an API/schema/permission change is intentional, then review the diff before committing.

```bash
PYTHONPATH=src:. GANTRY_SERVER__CONFIG_FILE=gantry.toml \
  uv run --group dev python tests/snapshots/update_snapshots.py
```

The generator updates:

- `*_operations.tsv`
- `*_operation_contracts.json`
- selected response schema snapshots
- `management_paths.txt`
- `permission_catalogs.json`
