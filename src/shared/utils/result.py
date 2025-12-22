from typing import TypeGuard

from safe_result import E, T, Err, Result


def err(result: Result[T, E]) -> TypeGuard[Err[E]]:
    return isinstance(result, Err)
