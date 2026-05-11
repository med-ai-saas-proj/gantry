from uuid import UUID

import fastuuid


__all__ = [
    "uuid7",
]


def uuid7() -> UUID:
    """Generate uuid V7."""
    return UUID(bytes=fastuuid.uuid7().bytes)
