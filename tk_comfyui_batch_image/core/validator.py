"""Schema validation with human-readable error messages."""
from __future__ import annotations

from collections.abc import Iterable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as _JsonSchemaError

from .schema import COMIC_SCHEMA


class ValidationError(Exception):
    """Raised when a comic script fails validation. Message lists all errors."""


def _format_path(path: Iterable) -> str:
    parts: list[str] = []
    for segment in path:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        else:
            parts.append(f".{segment}" if parts else str(segment))
    return "".join(parts) or "<root>"


def _format_error(err: _JsonSchemaError) -> str:
    path = _format_path(err.absolute_path)
    return f"  {path}\n    {err.message}"


def validate_schema(data: dict) -> None:
    """Validate `data` against the comic schema.

    Raises ValidationError listing ALL violations (not just the first) on failure.
    Returns None on success.
    """
    validator = Draft202012Validator(COMIC_SCHEMA)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if not errors:
        return None
    lines = ["Comic script validation failed:", ""]
    lines.extend(_format_error(e) for e in errors)
    raise ValidationError("\n".join(lines))
