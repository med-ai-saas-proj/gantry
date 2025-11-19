from typing import ClassVar


class RecoverableError(Exception):
    status: ClassVar[int] = 500
    title: ClassVar[str]
    code: ClassVar[str]
    detail: ClassVar[str | None] = None

    def __init__(self) -> None:
        super().__init__(self.format())

    def format(self):
        return {
            "status": self.status,
            "title": self.title,
            "code": self.code,
            "detail": self.detail,
        }


class UnrecoverableError(Exception):
    detail: ClassVar[str]
