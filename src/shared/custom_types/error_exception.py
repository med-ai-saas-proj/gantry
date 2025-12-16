from ..consts import messages_const
from ..settings import getAppSetting
from ..dtos.error_output import ProblemDetails

import traceback
from typing import ClassVar


class RecoverableError(Exception):
    status: ClassVar[int] = 500
    title: ClassVar[str]
    code: ClassVar[str | None] = None
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
        title = getattr(self, "title", messages_const.INTERNAL_SERVER_ERROR)
        res: ProblemDetails = {"status": self.status, "title": title}

        code = getattr(self, "code", None)
        if code:
            res.update({"code": code})

        detail = getattr(self, "detail", None)
        if detail:
            res.update({"detail": detail})

        return res


class UnrecoverableError(Exception):
    detail: ClassVar[str]
    _stack_frames: list[str]
    _from: Exception | None

    def __init__(self, from_exception: Exception | None = None):
        super().__init__()
        self._stack_frames = traceback.format_stack()
        self._from = from_exception
