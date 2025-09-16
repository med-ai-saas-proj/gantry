import uuid
from src.initialize.request_id import REQUEST_ID_CONTEXTVAR, REQUEST_ID_VARS


class RequestIdUtils:
    @staticmethod
    def get() -> str | None:
        context_id = REQUEST_ID_CONTEXTVAR.get()
        if context_id is None:
            return None
        return REQUEST_ID_VARS.get(context_id, None)

    @staticmethod
    def set(request_id: str) -> None:
        context_id = REQUEST_ID_CONTEXTVAR.get()
        if context_id is None:
            context_id = str(uuid.uuid4())
        REQUEST_ID_CONTEXTVAR.set(request_id)
        REQUEST_ID_VARS[context_id] = request_id

    @staticmethod
    def reset() -> None:
        context_id = REQUEST_ID_CONTEXTVAR.get()
        if context_id is None:
            return
        REQUEST_ID_VARS.pop(context_id, None)
        REQUEST_ID_CONTEXTVAR.set(None)
