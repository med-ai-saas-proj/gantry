from __future__ import annotations

from collections.abc import Iterable


def truncate_sql(tables: Iterable[str]) -> list[str]:
    return [f'TRUNCATE TABLE {table} RESTART IDENTITY CASCADE' for table in tables]
