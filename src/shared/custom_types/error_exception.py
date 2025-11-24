from ..settings import getAppSetting

import traceback
from typing import ClassVar


class RecoverableError(Exception):
    status: ClassVar[int] = 500
    title: ClassVar[str]
    code: ClassVar[str]
    detail: ClassVar[str | None] = None
    _stack_frames: list[str] | None

    def __init__(self) -> None:
        super().__init__(self.format())
        if getAppSetting().debug:
            self._stack_frames = traceback.format_stack()
        else:
            self._stack_frames = None

    def format(self):
        return {
            "status": self.status,
            "title": self.title,
            "code": self.code,
            "detail": self.detail,
        }


class UnrecoverableError(Exception):
    detail: ClassVar[str]
    _stack_frames: list[str]

    def __init__(self):
        super().__init__()
        self._stack_frames = traceback.format_stack()
