"""Validation helpers for dataset paths, filenames, and label extensions."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Iterable, Protocol


SUPPORTED_IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
)
WINDOWS_FORBIDDEN = frozenset('<>:"/\\|?*')
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


class HasLabelPath(Protocol):
    label_path: PurePosixPath


def is_supported_image(path: str | Path | PurePosixPath) -> bool:
    """Return whether *path* has a supported image suffix, case-insensitively."""

    return Path(str(path)).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def validate_extension(extension: str) -> tuple[bool, str]:
    """Validate an already-normalized label extension."""

    if not extension or extension == ".":
        return False, "Enter a label extension such as .txt or .bbox."
    if not extension.startswith("."):
        return False, "The extension must begin with a period."
    if len(extension) > 33:
        return False, "The extension must be 32 characters or fewer."
    if any(char in WINDOWS_FORBIDDEN or ord(char) < 32 for char in extension):
        return False, "The extension contains an unsafe character."
    if any(char.isspace() for char in extension):
        return False, "The extension cannot contain whitespace."
    if extension.endswith(".") or ".." in extension:
        return False, "The extension cannot contain empty dot-separated parts."
    return True, ""


def validate_filename(filename: str) -> tuple[bool, str]:
    """Validate one filename for safe, portable ZIP creation."""

    if not filename or filename in {".", ".."}:
        return False, "Filename is empty or reserved."
    if any(char in WINDOWS_FORBIDDEN or ord(char) < 32 for char in filename):
        return False, "Filename contains a character that is unsafe on Windows."
    if filename.endswith((" ", ".")):
        return False, "Filename cannot end with a space or period on Windows."
    if filename.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        return False, "Filename is reserved on Windows."
    return True, ""


def validate_relative_path(path: PurePosixPath) -> tuple[bool, str]:
    """Reject absolute, traversing, or non-portable uploaded paths."""

    if path.is_absolute() or not path.parts:
        return False, "Path must be relative."
    if any(part in {"", ".", ".."} for part in path.parts):
        return False, "Path contains an unsafe traversal component."
    for part in path.parts:
        valid, reason = validate_filename(part)
        if not valid:
            return False, reason
    return True, ""


def detect_collisions(mappings: Iterable[HasLabelPath]) -> dict[str, list[HasLabelPath]]:
    """Group output paths that collide on case-insensitive filesystems."""

    grouped: dict[str, list[HasLabelPath]] = defaultdict(list)
    for mapping in mappings:
        grouped[mapping.label_path.as_posix().casefold()].append(mapping)
    return {key: values for key, values in grouped.items() if len(values) > 1}
