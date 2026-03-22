"""Implementation of result type."""

from __future__ import annotations

from enum import Enum
from typing import Generic, Literal, TypeVar, Callable, TypeAlias
from dataclasses import dataclass


T = TypeVar("T", covariant=True)
E = TypeVar("E", covariant=True)
U = TypeVar("U")
V = TypeVar("V")


class ResultStatus(Enum):
    """Result status."""

    Ok = 0
    Err = 1


@dataclass
class _Result(Generic[T, E]):
    value: T | E
    status: ResultStatus

    def ok(self) -> T | None:
        """Get success value, discard the error, if error return None."""
        if self.status == ResultStatus.Ok:
            return self.value
        return None

    def err(self) -> E | None:
        """Get error value, discard the success value, if success return None."""
        if self.status == ResultStatus.Err:
            return self.value
        return None

    def unwrap(self) -> T:
        """Get success value, raise the error if raiseable, else raise RuntimeError(error)."""
        if self.status == ResultStatus.Err:
            if isinstance(self.value, BaseException):
                raise self.value
            raise RuntimeError(self.value)
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get success value, if error return default."""
        if self.status == ResultStatus.Err:
            return default
        return self.value

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Apply fn to success value, leave the error value untouched."""
        if self.status == ResultStatus.Ok:
            return Ok(fn(self.value))
        return self

    def map_err(self, fn: Callable[[E], U]) -> Result[T, U]:
        """Apply fn to error value, leave the success value untouched."""
        if self.status == ResultStatus.Err:
            return Err(fn(self.value))
        return self

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Apply fn to this result if success, leave the error value untouched."""
        if self.status == ResultStatus.Ok:
            return fn(self.value)
        return self


@dataclass
class Ok(_Result[T, E]):
    """Result's success state, shorter construction and pattern matching."""

    value: T
    status: Literal[ResultStatus.Ok]

    def __init__(self, value: T):
        """Construct a new Result with status = .Ok (The function succeed)."""
        super().__init__(value, ResultStatus.Ok)


@dataclass
class Err(_Result[T, E]):
    """Result's error state, shorter construction and pattern matching."""

    value: E
    status: Literal[ResultStatus.Err]

    def __init__(self, value: E):
        """Construct a new Result with status = .Err (The function failed)."""
        super().__init__(value, ResultStatus.Err)

    def into(self) -> Result[U, E]:
        """Convert this Result(Err) to another result with the same or wider error type."""
        return Err(self.value)


Result: TypeAlias = Ok[T, E] | Err[T, E]
