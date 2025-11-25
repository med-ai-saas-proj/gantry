from ..settings import getAppSetting
from ..dtos.error_output import ProblemDetails

import traceback
from typing import ClassVar


class RecoverableError(Exception):
    status: ClassVar[int] = 500
    title: ClassVar[str]
    code: ClassVar[str]
    detail: ClassVar[str | None] = None
    _stack_frames: list[str] | None
    _from: Exception | None

    def __init__(self, from_exception: Exception | None = None) -> None:
        super().__init__(self.format())
        if getAppSetting().debug:
            self._stack_frames = traceback.format_stack()
        else:
            self._stack_frames = None

        self._from = from_exception

    def format(self) -> ProblemDetails:
        res: ProblemDetails = {"status": self.status, "title": self.title}
        if self.code:
            res.update({"code": self.code})
        if self.detail:
            res.update({"detail": self.detail})
        return res


class UnrecoverableError(Exception):
    detail: ClassVar[str]
    _stack_frames: list[str]
    _from: Exception | None

    def __init__(self, from_exception: Exception | None = None):
        super().__init__()
        self._stack_frames = traceback.format_stack()
        self._from = from_exception
