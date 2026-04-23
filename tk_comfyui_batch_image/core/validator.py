"""Schema + semantic validation with human-readable error messages."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from jsonschema import Draft202012Validator

from .schema import COMIC_SCHEMA


class ValidationError(Exception):
    """Raised when a comic script fails validation. Message lists all errors."""


@dataclass(frozen=True)
class CheckError:
    """A single validation failure in a form both human and JSON outputs can use."""
    layer: int            # 1 = JSON schema, 2 = semantic rule
    path: str             # e.g. "pages[0].panels[2].width_px" or "<root>"
    message: str
    hint: str | None = None


def _format_path(path: Iterable) -> str:
    parts: list[str] = []
    for segment in path:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        else:
            parts.append(f".{segment}" if parts else str(segment))
    return "".join(parts) or "<root>"


def _schema_errors(data: dict) -> list[CheckError]:
    v = Draft202012Validator(COMIC_SCHEMA)
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.absolute_path))
    return [
        CheckError(layer=1, path=_format_path(e.absolute_path), message=e.message)
        for e in errs
    ]


def r_page_index_continuity(data: dict) -> list[CheckError]:
    errors: list[CheckError] = []
    for i, page in enumerate(data.get("pages", [])):
        expected = i + 1
        got = page.get("page_index")
        if got != expected:
            errors.append(CheckError(
                layer=2,
                path=f"pages[{i}].page_index",
                message=f"expected {expected}, got {got} (pages must be contiguous from 1)",
            ))
    return errors


def r_panel_index_continuity(data: dict) -> list[CheckError]:
    errors: list[CheckError] = []
    for i, page in enumerate(data.get("pages", [])):
        for j, panel in enumerate(page.get("panels", [])):
            expected = j + 1
            got = panel.get("panel_index")
            if got != expected:
                errors.append(CheckError(
                    layer=2,
                    path=f"pages[{i}].panels[{j}].panel_index",
                    message=f"expected {expected}, got {got} "
                            f"(panels within a page must be contiguous from 1)",
                ))
    return errors


def r_layout_fits_page(data: dict) -> list[CheckError]:
    errors: list[CheckError] = []
    page_height = data.get("page_height_px")
    bleed = data.get("bleed_px", 0)
    book_gutter = data.get("gutter_px", 0)

    if page_height is None:
        return errors  # R5 will catch this for page_template="custom"

    inner_h = page_height - bleed * 2
    for i, page in enumerate(data.get("pages", [])):
        if page.get("layout_mode") != "vertical_stack":
            continue
        gutter = page.get("gutter_px", book_gutter)
        panels = page.get("panels", [])
        panel_total = sum(p.get("height_px", 0) for p in panels)
        gutter_total = max(0, len(panels) - 1) * gutter
        used = panel_total + gutter_total
        if used > inner_h:
            errors.append(CheckError(
                layer=2,
                path=f"pages[{i}]",
                message=f"total height {panel_total}px (panels) + {gutter_total}px (gutters) "
                        f"= {used}px exceeds inner area {inner_h}px "
                        f"(= {page_height} - bleed {bleed}*2)",
                hint="reduce a panel height, lower gutter_px, or raise page_height_px",
            ))
    return errors


_LAYER2_RULES: list[Callable[[dict], list[CheckError]]] = [
    r_page_index_continuity,
    r_panel_index_continuity,
    r_layout_fits_page,
]


def _semantic_errors(data: dict) -> list[CheckError]:
    result: list[CheckError] = []
    for rule in _LAYER2_RULES:
        result.extend(rule(data))
    return result


def collect_errors(data: dict) -> list[CheckError]:
    """Return ALL validation errors as a flat list. Schema errors short-circuit
    semantic checks because the latter assume the former's structure holds."""
    schema_errs = _schema_errors(data)
    if schema_errs:
        return schema_errs
    return _semantic_errors(data)


def _format_human(errors: list[CheckError]) -> str:
    lines = ["Comic script validation failed:", ""]
    for e in errors:
        block = [f"  [L{e.layer}] {e.path}", f"    {e.message}"]
        if e.hint:
            block.append(f"    hint: {e.hint}")
        lines.append("\n".join(block))
    return "\n".join(lines)


def validate(data: dict) -> None:
    """Run Layer 1 + Layer 2 validation. Raise ValidationError with all errors."""
    errors = collect_errors(data)
    if errors:
        raise ValidationError(_format_human(errors))


def validate_schema(data: dict) -> None:
    """Backwards-compatible alias. Prefer validate() for new call sites."""
    validate(data)
