from typing import BinaryIO

from filetype import filetype


def detect_file_type(stream: BinaryIO | bytes) -> tuple[str, str | None]:
    """Detect MIME type and extension from first bytes of BinaryIO."""
    if isinstance(stream, bytes):
        try:
            kind = filetype.guess(stream)
            if kind:
                return kind.mime, kind.extension
            return "application/octet-stream", None
        except TypeError:
            return "application/octet-stream", None

    head = stream.read(1024)
    stream.seek(0)  # Reset stream position
    try:
        kind = filetype.guess(head)
        if kind:
            return kind.mime, kind.extension
        return "application/octet-stream", None
    except TypeError:
        return "application/octet-stream", None
