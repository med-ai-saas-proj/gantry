import mimetypes
from typing import BinaryIO

from filetype import filetype


def detect_file_type(stream: BinaryIO | bytes):
    """Detect MIME type and extension from first bytes of BinaryIO."""
    if isinstance(stream, bytes):
        try:
            kind = filetype.guess(stream)
            if kind:
                return kind.mime, kind.extension
            return "application/octet-stream", "bin"
        except TypeError:
            return "application/octet-stream", "bin"

    head = stream.read(1024)
    stream.seek(0)  # Reset stream position
    try:
        kind = filetype.guess(head)
        if kind:
            return kind.mime, kind.extension
        return "application/octet-stream", "bin"
    except TypeError:
        return "application/octet-stream", "bin"


def remove_extension(filename: str) -> str:
    """Remove the file extension from a filename."""
    if filename.startswith(".") and filename.count(".") == 1:
        return filename  # Hidden file with no extension

    if "." in filename:
        return ".".join(filename.split(".")[:-1])
    return filename
