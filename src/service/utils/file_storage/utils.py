from typing import BinaryIO

from filetype import filetype


def detect_file_type(stream: BinaryIO):
    """Detect MIME type and extension from first bytes of BinaryIO."""
    head = stream.read(261)  # Read first 261 bytes (enough for filetype)
    stream.seek(0)  # Reset stream position
    kind = filetype.guess(head)
    if kind:
        return kind.mime, kind.extension
    return "application/octet-stream", ""


def remove_extension(filename: str) -> str:
    """Remove the file extension from a filename."""
    if filename.startswith(".") and filename.count(".") == 1:
        return filename  # Hidden file with no extension

    if "." in filename:
        return ".".join(filename.split(".")[:-1])
    return filename
