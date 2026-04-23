# Comic Batch M2 — Validation & Skill Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Layer-2 semantic validator, a standalone CLI, and a skill-pack (SKILL.md / PROMPT_TEMPLATE.md / README.md / schema.json / 5 examples) so that an AI acting as a manga panel composition expert can produce validated comic JSONs end-to-end without opening ComfyUI.

**Architecture:**
- `core/validator.py` grows a pluggable list of semantic-rule functions that return structured `CheckError` values. Both the CLI and the existing `ComicScriptLoader` consume the same `validate()` / `collect_errors()` entry points — single source of truth for validation behavior.
- A thin CLI (`validate.py`) wraps I/O, argument parsing, and dual output modes (human-readable + `--json`).
- `schema_export.py` serializes the Python `COMIC_SCHEMA` dict into the skill pack's `schema.json`; a pytest-based drift test guarantees the two never diverge.
- The skill pack lives under `docs/skills/comic-script-authoring/`. Authoring docs deliberately avoid duplicating schema field tables — they link back to `schema.json`.

**Tech Stack:** Python 3.11+, `jsonschema`, `argparse` (stdlib), `pytest`, `ruff`. No new runtime deps.

**Reference:** Spec at `docs/superpowers/specs/2026-04-23-comfyui-comic-batch-m2-validation-skill.md`.

---

## File Structure

### Files to create

| Path | Responsibility |
|---|---|
| `tk_comfyui_batch_image/validate.py` | CLI entry point (`python -m tk_comfyui_batch_image.validate`); argparse, I/O, output formatting, exit codes. |
| `tk_comfyui_batch_image/schema_export.py` | Serialize `core/schema.COMIC_SCHEMA` → `docs/skills/comic-script-authoring/schema.json`. |
| `tk_comfyui_batch_image/tests/test_validator_layer2.py` | Unit tests for the 5 Layer-2 rules. |
| `tk_comfyui_batch_image/tests/test_cli_validate.py` | Tests for CLI exit codes, output formatting, truncation. |
| `tk_comfyui_batch_image/tests/test_schema_export.py` | Drift test (`schema.json` vs `core/schema.COMIC_SCHEMA`). |
| `tk_comfyui_batch_image/tests/test_examples_valid.py` | Parametric regression test (every example's `output.json` validates). |
| `docs/skills/comic-script-authoring/schema.json` | Generated from `core/schema.py`; committed alongside the exporter. |
| `docs/skills/comic-script-authoring/SKILL.md` | Claude Code / superpowers-format skill file. |
| `docs/skills/comic-script-authoring/PROMPT_TEMPLATE.md` | System-prompt version for generic LLMs. |
| `docs/skills/comic-script-authoring/README.md` | For humans using the tool, not for JSON writers. |
| `docs/skills/comic-script-authoring/examples/01_minimal/screenplay.md` | Minimal example screenplay. |
| `docs/skills/comic-script-authoring/examples/01_minimal/output.json` | Expected JSON output from AI. |
| `docs/skills/comic-script-authoring/examples/02_vertical_stack_3panel/screenplay.md` | Teaches vertical_stack + align. |
| `docs/skills/comic-script-authoring/examples/02_vertical_stack_3panel/output.json` | — |
| `docs/skills/comic-script-authoring/examples/03_per_panel_override/screenplay.md` | Teaches per-panel sampler_override. |
| `docs/skills/comic-script-authoring/examples/03_per_panel_override/output.json` | — |
| `docs/skills/comic-script-authoring/examples/04_rtl_reading/screenplay.md` | Teaches reading_direction=rtl. |
| `docs/skills/comic-script-authoring/examples/04_rtl_reading/output.json` | — |
| `docs/skills/comic-script-authoring/examples/05_character_prompt_style/screenplay.md` | Teaches 4-layer prompt stacking. |
| `docs/skills/comic-script-authoring/examples/05_character_prompt_style/output.json` | — |

### Files to modify

| Path | Change |
|---|---|
| `tk_comfyui_batch_image/core/validator.py` | Introduce `CheckError` dataclass + `collect_errors()` + `validate()`; keep the existing `validate_schema()` as a thin alias (it already raises `ValidationError`). Layer-2 rules live in the same file for now — small enough and share the path-formatting helper. |
| `tk_comfyui_batch_image/nodes/script_loader.py:77` | Replace `validate_schema(data)` with `validate(data)` so the in-node safety net covers Layer 2 too. |
| `tk_comfyui_batch_image/tests/test_validator.py` | No behavior change needed — existing schema fixtures stay valid. Tests continue to assert `ValidationError` is raised on malformed input; verify still pass. |

---

## Task 1: Introduce CheckError + collect_errors scaffold in core/validator.py

**Files:**
- Modify: `tk_comfyui_batch_image/core/validator.py`
- Test: `tk_comfyui_batch_image/tests/test_validator_layer2.py` (new, bootstrap only)

- [ ] **Step 1: Write a failing test that imports the new scaffold**

Create `tk_comfyui_batch_image/tests/test_validator_layer2.py` with:

```python
"""Tests for Layer-2 semantic validator rules (M2)."""
from tk_comfyui_batch_image.core.validator import (
    CheckError,
    collect_errors,
    validate,
)


def test_checkerror_dataclass_shape():
    e = CheckError(layer=2, path="pages[0]", message="boom", hint="try this")
    assert e.layer == 2
    assert e.path == "pages[0]"
    assert e.message == "boom"
    assert e.hint == "try this"


def test_collect_errors_returns_list_for_valid_minimal_script():
    data = _minimal_valid_book()
    assert collect_errors(data) == []


def test_validate_raises_on_invalid_schema():
    import pytest
    from tk_comfyui_batch_image.core.validator import ValidationError
    with pytest.raises(ValidationError):
        validate({})   # empty dict fails schema required-field check


def _minimal_valid_book() -> dict:
    return {
        "version": "1.0",
        "job_id": "test",
        "reading_direction": "ltr",
        "page_template": "custom",
        "page_width_px": 1080,
        "page_height_px": 1920,
        "bleed_px": 20,
        "gutter_px": 10,
        "page_background": "#FFFFFF",
        "base_seed": 0,
        "style_prompt":     {"positive": "", "negative": ""},
        "character_prompt": {"positive": "", "negative": ""},
        "default_sampler": {
            "sampler_name": "euler", "scheduler": "normal",
            "steps": 20, "cfg": 7.0, "denoise": 1.0,
        },
        "default_border": {"width_px": 2, "color": "#000000", "style": "solid"},
        "pages": [{
            "page_index": 1,
            "page_prompt": {"positive": "", "negative": ""},
            "layout_mode": "vertical_stack",
            "panels": [{
                "panel_index": 1,
                "scene_prompt": {"positive": "scene", "negative": ""},
                "width_px": 1040, "height_px": 600,
                "align": "center",
                "shape": {"type": "rect"},
            }],
        }],
    }
```

- [ ] **Step 2: Run the test and verify it fails with ImportError**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -v`
Expected: `ImportError: cannot import name 'CheckError' from ...`

- [ ] **Step 3: Implement the scaffold in core/validator.py**

Replace the contents of `tk_comfyui_batch_image/core/validator.py` with:

```python
"""Schema + semantic validation with human-readable error messages."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as _JsonSchemaError

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


_LAYER2_RULES: list[Callable[[dict], list[CheckError]]] = []
"""Populated by later tasks — keep empty for scaffold task."""


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
```

- [ ] **Step 4: Run the scaffold tests — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run the full existing suite to make sure nothing regressed**

Run: `pytest tk_comfyui_batch_image/tests/ -q`
Expected: all previously-passing tests still pass (74 from M1 + 3 new = 77).

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/core/validator.py tk_comfyui_batch_image/tests/test_validator_layer2.py
git commit -m "feat(validator): scaffold CheckError + collect_errors for Layer 2"
```

---

## Task 2: Rule R1 — page_index continuity

**Files:**
- Modify: `tk_comfyui_batch_image/core/validator.py`
- Test: `tk_comfyui_batch_image/tests/test_validator_layer2.py`

- [ ] **Step 1: Write the failing tests**

Append to `tk_comfyui_batch_image/tests/test_validator_layer2.py`:

```python
def _book_with_pages(page_indexes: list[int]) -> dict:
    book = _minimal_valid_book()
    template = book["pages"][0]
    book["pages"] = [{**template, "page_index": idx} for idx in page_indexes]
    return book


def test_r1_page_index_sequential_from_one_passes():
    assert collect_errors(_book_with_pages([1, 2, 3])) == []


def test_r1_page_index_gap_is_caught():
    errs = collect_errors(_book_with_pages([1, 3, 4]))
    assert len(errs) == 1
    assert errs[0].layer == 2
    assert errs[0].path == "pages[1].page_index"
    assert "expected 2" in errs[0].message
    assert "got 3" in errs[0].message


def test_r1_page_index_starts_at_wrong_number():
    errs = collect_errors(_book_with_pages([2, 3]))
    assert len(errs) >= 1
    assert errs[0].path == "pages[0].page_index"


def test_r1_page_index_duplicate():
    errs = collect_errors(_book_with_pages([1, 1]))
    assert any("pages[1].page_index" in e.path for e in errs)
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r1 -v`
Expected: all 4 FAIL (rule not implemented yet).

- [ ] **Step 3: Implement r_page_index_continuity**

In `tk_comfyui_batch_image/core/validator.py`, add immediately above the `_LAYER2_RULES = []` line:

```python
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
```

And change the `_LAYER2_RULES` declaration to:

```python
_LAYER2_RULES: list[Callable[[dict], list[CheckError]]] = [
    r_page_index_continuity,
]
```

- [ ] **Step 4: Run R1 tests — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r1 -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/validator.py tk_comfyui_batch_image/tests/test_validator_layer2.py
git commit -m "feat(validator): R1 page_index continuity"
```

---

## Task 3: Rule R2 — panel_index continuity per page

**Files:**
- Modify: `tk_comfyui_batch_image/core/validator.py`
- Test: `tk_comfyui_batch_image/tests/test_validator_layer2.py`

- [ ] **Step 1: Write the failing tests**

Append to `tk_comfyui_batch_image/tests/test_validator_layer2.py`:

```python
def _book_with_panel_indexes_on_page_0(panel_indexes: list[int]) -> dict:
    book = _minimal_valid_book()
    panel_template = book["pages"][0]["panels"][0]
    book["pages"][0]["panels"] = [
        {**panel_template, "panel_index": idx} for idx in panel_indexes
    ]
    # Height fits: total panel height stays within page inner area.
    for p in book["pages"][0]["panels"]:
        p["height_px"] = 300
    return book


def test_r2_panel_index_sequential_passes():
    assert collect_errors(_book_with_panel_indexes_on_page_0([1, 2, 3])) == []


def test_r2_panel_index_gap_is_caught():
    errs = collect_errors(_book_with_panel_indexes_on_page_0([1, 3]))
    assert any(e.path == "pages[0].panels[1].panel_index" for e in errs)
    assert any("expected 2" in e.message for e in errs)


def test_r2_panel_index_out_of_order():
    errs = collect_errors(_book_with_panel_indexes_on_page_0([2, 1]))
    assert any(e.path == "pages[0].panels[0].panel_index" for e in errs)
```

- [ ] **Step 2: Run tests — fail**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r2 -v`
Expected: 3 FAIL.

- [ ] **Step 3: Implement r_panel_index_continuity**

In `tk_comfyui_batch_image/core/validator.py`, add below `r_page_index_continuity`:

```python
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
```

Append to `_LAYER2_RULES`:

```python
_LAYER2_RULES: list[Callable[[dict], list[CheckError]]] = [
    r_page_index_continuity,
    r_panel_index_continuity,
]
```

- [ ] **Step 4: Run R2 tests — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r2 -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/validator.py tk_comfyui_batch_image/tests/test_validator_layer2.py
git commit -m "feat(validator): R2 panel_index continuity"
```

---

## Task 4: Rule R3 — vertical_stack layout fits page height

**Files:**
- Modify: `tk_comfyui_batch_image/core/validator.py`
- Test: `tk_comfyui_batch_image/tests/test_validator_layer2.py`

- [ ] **Step 1: Write the failing tests**

Append to `tk_comfyui_batch_image/tests/test_validator_layer2.py`:

```python
def test_r3_layout_fits_exact_edge_passes():
    """page_height=768, bleed=20 → inner=728; 3x200 panels + 2x64 gutter = 728."""
    book = _minimal_valid_book()
    book["page_height_px"] = 768
    book["bleed_px"] = 20
    book["gutter_px"] = 64
    template = book["pages"][0]["panels"][0]
    book["pages"][0]["panels"] = [
        {**template, "panel_index": i + 1, "height_px": 200, "width_px": 1040}
        for i in range(3)
    ]
    assert collect_errors(book) == []


def test_r3_total_height_exceeds_inner_area():
    book = _minimal_valid_book()
    book["page_height_px"] = 768
    book["bleed_px"] = 20
    book["gutter_px"] = 10
    template = book["pages"][0]["panels"][0]
    book["pages"][0]["panels"] = [
        {**template, "panel_index": i + 1, "height_px": 400, "width_px": 1040}
        for i in range(2)
    ]
    # 800 + 10 = 810 > 728
    errs = collect_errors(book)
    assert any(e.path == "pages[0]" for e in errs)
    match = next(e for e in errs if e.path == "pages[0]")
    assert "810" in match.message
    assert "728" in match.message
    assert match.hint is not None


def test_r3_page_level_gutter_override_wins():
    book = _minimal_valid_book()
    book["page_height_px"] = 768
    book["bleed_px"] = 20
    book["gutter_px"] = 100     # book-level would exceed
    book["pages"][0]["gutter_px"] = 10   # page-level override fits
    template = book["pages"][0]["panels"][0]
    book["pages"][0]["panels"] = [
        {**template, "panel_index": i + 1, "height_px": 300, "width_px": 1040}
        for i in range(2)
    ]
    # With page gutter=10: 600 + 10 = 610 ≤ 728 ✓
    assert collect_errors(book) == []
```

- [ ] **Step 2: Run tests — fail**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r3 -v`
Expected: 3 FAIL.

- [ ] **Step 3: Implement r_layout_fits_page**

In `tk_comfyui_batch_image/core/validator.py`, add below `r_panel_index_continuity`:

```python
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
```

Append to `_LAYER2_RULES`:

```python
_LAYER2_RULES: list[Callable[[dict], list[CheckError]]] = [
    r_page_index_continuity,
    r_panel_index_continuity,
    r_layout_fits_page,
]
```

- [ ] **Step 4: Run R3 tests — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r3 -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/validator.py tk_comfyui_batch_image/tests/test_validator_layer2.py
git commit -m "feat(validator): R3 vertical_stack layout fits page"
```

---

## Task 5: Rule R4 — panel width fits page width

**Files:**
- Modify: `tk_comfyui_batch_image/core/validator.py`
- Test: `tk_comfyui_batch_image/tests/test_validator_layer2.py`

- [ ] **Step 1: Write the failing tests**

Append to `tk_comfyui_batch_image/tests/test_validator_layer2.py`:

```python
def test_r4_panel_width_fits_passes():
    book = _minimal_valid_book()
    book["page_width_px"] = 1080
    book["bleed_px"] = 20
    book["pages"][0]["panels"][0]["width_px"] = 1040
    assert collect_errors(book) == []


def test_r4_panel_width_exceeds_inner_width():
    book = _minimal_valid_book()
    book["page_width_px"] = 1080
    book["bleed_px"] = 20
    book["pages"][0]["panels"][0]["width_px"] = 1100
    errs = collect_errors(book)
    match = next(e for e in errs if "panels[0]" in e.path)
    assert match.path == "pages[0].panels[0]"
    assert "1100" in match.message
    assert "1040" in match.message
    assert match.hint is not None
```

- [ ] **Step 2: Run tests — fail**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r4 -v`
Expected: 2 FAIL.

- [ ] **Step 3: Implement r_panel_width_fits**

In `tk_comfyui_batch_image/core/validator.py`, add below `r_layout_fits_page`:

```python
def r_panel_width_fits(data: dict) -> list[CheckError]:
    errors: list[CheckError] = []
    page_width = data.get("page_width_px")
    bleed = data.get("bleed_px", 0)
    if page_width is None:
        return errors  # R5 handles missing width for custom templates
    inner_w = page_width - bleed * 2
    for i, page in enumerate(data.get("pages", [])):
        for j, panel in enumerate(page.get("panels", [])):
            w = panel.get("width_px", 0)
            if w > inner_w:
                errors.append(CheckError(
                    layer=2,
                    path=f"pages[{i}].panels[{j}]",
                    message=f"width {w}px exceeds inner width {inner_w}px "
                            f"(= {page_width} - bleed {bleed}*2)",
                    hint="reduce panel.width_px or raise page_width_px",
                ))
    return errors
```

Append to `_LAYER2_RULES`:

```python
_LAYER2_RULES: list[Callable[[dict], list[CheckError]]] = [
    r_page_index_continuity,
    r_panel_index_continuity,
    r_layout_fits_page,
    r_panel_width_fits,
]
```

- [ ] **Step 4: Run R4 tests — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r4 -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/validator.py tk_comfyui_batch_image/tests/test_validator_layer2.py
git commit -m "feat(validator): R4 panel width fits page"
```

---

## Task 6: Rule R5 — page_template vs explicit dimensions

**Files:**
- Modify: `tk_comfyui_batch_image/core/validator.py`
- Test: `tk_comfyui_batch_image/tests/test_validator_layer2.py`

- [ ] **Step 1: Write the failing tests**

Append to `tk_comfyui_batch_image/tests/test_validator_layer2.py`:

```python
def test_r5_custom_template_with_explicit_size_passes():
    book = _minimal_valid_book()   # already has custom + both sizes
    assert collect_errors(book) == []


def test_r5_custom_template_missing_width_fails():
    book = _minimal_valid_book()
    del book["page_width_px"]
    errs = collect_errors(book)
    match = next(e for e in errs if e.layer == 2 and e.path == "<root>")
    assert "page_width_px" in match.message
    assert "custom" in match.message


def test_r5_custom_template_missing_height_fails():
    book = _minimal_valid_book()
    del book["page_height_px"]
    errs = collect_errors(book)
    match = next(e for e in errs if e.layer == 2 and e.path == "<root>")
    assert "page_height_px" in match.message


def test_r5_preset_template_rejects_explicit_width():
    book = _minimal_valid_book()
    book["page_template"] = "A4"
    # page_width_px still present -> reject
    errs = collect_errors(book)
    match = next(e for e in errs if e.layer == 2 and e.path == "<root>")
    assert "A4" in match.message
    assert "page_width_px" in match.message


def test_r5_preset_template_without_explicit_size_passes():
    book = _minimal_valid_book()
    book["page_template"] = "A4"
    del book["page_width_px"]
    del book["page_height_px"]
    # R3/R4 can't run without sizes, so they're no-ops; R5 is the only rule that
    # fires on this shape, and it should stay silent.
    errs = [e for e in collect_errors(book) if e.layer == 2]
    assert errs == []
```

- [ ] **Step 2: Run tests — fail**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r5 -v`
Expected: 4 FAIL (first test currently passes).

- [ ] **Step 3: Implement r_page_template_dim_consistency**

In `tk_comfyui_batch_image/core/validator.py`, add below `r_panel_width_fits`:

```python
def r_page_template_dim_consistency(data: dict) -> list[CheckError]:
    errors: list[CheckError] = []
    template = data.get("page_template")
    has_width = "page_width_px" in data
    has_height = "page_height_px" in data

    if template == "custom":
        missing = [k for k, present in
                   [("page_width_px", has_width), ("page_height_px", has_height)]
                   if not present]
        if missing:
            errors.append(CheckError(
                layer=2,
                path="<root>",
                message=f"page_template=\"custom\" requires {' and '.join(missing)}",
                hint="either add the missing dimension(s) or pick a preset page_template",
            ))
    elif template in {"A4", "B5", "JP_Tankobon", "Webtoon"}:
        provided = [k for k, present in
                    [("page_width_px", has_width), ("page_height_px", has_height)]
                    if present]
        if provided:
            errors.append(CheckError(
                layer=2,
                path="<root>",
                message=f"page_template=\"{template}\" must not coexist with "
                        f"explicit {' / '.join(provided)} — pick one source of truth",
                hint='set page_template="custom" if you want to specify dimensions explicitly',
            ))
    return errors
```

Append to `_LAYER2_RULES`:

```python
_LAYER2_RULES: list[Callable[[dict], list[CheckError]]] = [
    r_page_index_continuity,
    r_panel_index_continuity,
    r_layout_fits_page,
    r_panel_width_fits,
    r_page_template_dim_consistency,
]
```

- [ ] **Step 4: Run R5 tests — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_validator_layer2.py -k r5 -v`
Expected: 5 passed (including the pre-existing happy-path test).

- [ ] **Step 5: Run the full Layer-2 file + M1 suite**

Run: `pytest tk_comfyui_batch_image/tests/ -q`
Expected: all tests pass (M1 74 + scaffold 3 + R1 4 + R2 3 + R3 3 + R4 2 + R5 5 = 94).

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/core/validator.py tk_comfyui_batch_image/tests/test_validator_layer2.py
git commit -m "feat(validator): R5 page_template vs explicit dimensions"
```

---

## Task 7: Upgrade script_loader to call validate() and verify M1 regression

**Files:**
- Modify: `tk_comfyui_batch_image/nodes/script_loader.py`
- Inspect: `tk_comfyui_batch_image/tests/test_script_loader.py`, `tk_comfyui_batch_image/tests/test_validator.py`

- [ ] **Step 1: Read the current validate call site**

Open `tk_comfyui_batch_image/nodes/script_loader.py` line 77 region. Confirm the import line is:

```python
from ..core.validator import validate_schema
```

and the call is `validate_schema(data)`.

- [ ] **Step 2: Replace with validate**

Change the import:

```python
from ..core.validator import validate
```

Change the call:

```python
validate(data)
```

Leave everything else in the file untouched.

- [ ] **Step 3: Run the full suite — must stay green**

Run: `pytest tk_comfyui_batch_image/tests/ -q`
Expected: 94 passed. No Layer-2 regression in existing fixtures (they are all compliant).

If any existing fixture fails Layer 2, fix the fixture to be genuinely valid (do not relax the rule). Then re-run.

- [ ] **Step 4: Commit**

```bash
git add tk_comfyui_batch_image/nodes/script_loader.py
git commit -m "refactor(script_loader): use validate() for Layer 1 + Layer 2 safety net"
```

---

## Task 8: CLI skeleton with exit codes and human-readable output

**Files:**
- Create: `tk_comfyui_batch_image/validate.py`
- Test: `tk_comfyui_batch_image/tests/test_cli_validate.py`

- [ ] **Step 1: Write the failing tests for single-file exit codes**

Create `tk_comfyui_batch_image/tests/test_cli_validate.py` with:

```python
"""Tests for the standalone validate CLI."""
import json
from pathlib import Path

import pytest

from tk_comfyui_batch_image.validate import main


def _write(tmp_path: Path, name: str, body: dict | str) -> Path:
    p = tmp_path / name
    p.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return p


def _valid_minimal_book() -> dict:
    return {
        "version": "1.0", "job_id": "cli_test", "reading_direction": "ltr",
        "page_template": "custom", "page_width_px": 1080, "page_height_px": 1920,
        "bleed_px": 20, "gutter_px": 10, "page_background": "#FFFFFF", "base_seed": 0,
        "style_prompt":     {"positive": "", "negative": ""},
        "character_prompt": {"positive": "", "negative": ""},
        "default_sampler": {
            "sampler_name": "euler", "scheduler": "normal",
            "steps": 20, "cfg": 7.0, "denoise": 1.0},
        "default_border": {"width_px": 2, "color": "#000000", "style": "solid"},
        "pages": [{
            "page_index": 1,
            "page_prompt": {"positive": "", "negative": ""},
            "layout_mode": "vertical_stack",
            "panels": [{
                "panel_index": 1,
                "scene_prompt": {"positive": "s", "negative": ""},
                "width_px": 1040, "height_px": 600,
                "align": "center", "shape": {"type": "rect"},
            }],
        }],
    }


def test_cli_no_args_returns_exit_2(capsys):
    code = main([])
    assert code == 2
    out = capsys.readouterr()
    assert "usage" in (out.out + out.err).lower()


def test_cli_single_valid_file_exits_0(tmp_path, capsys):
    p = _write(tmp_path, "ok.json", _valid_minimal_book())
    code = main([str(p)])
    assert code == 0
    assert "✓" in capsys.readouterr().out


def test_cli_single_invalid_file_exits_1(tmp_path, capsys):
    book = _valid_minimal_book()
    book["pages"][0]["page_index"] = 5
    p = _write(tmp_path, "bad.json", book)
    code = main([str(p)])
    assert code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "[L2]" in out


def test_cli_missing_file_exits_3(tmp_path, capsys):
    code = main([str(tmp_path / "nope.json")])
    assert code == 3


def test_cli_unreadable_json_exits_3(tmp_path, capsys):
    p = _write(tmp_path, "broken.json", "{not json")
    code = main([str(p)])
    assert code == 3
```

- [ ] **Step 2: Run tests — fail**

Run: `pytest tk_comfyui_batch_image/tests/test_cli_validate.py -v`
Expected: ImportError on `tk_comfyui_batch_image.validate`.

- [ ] **Step 3: Create the CLI module**

Create `tk_comfyui_batch_image/validate.py` with:

```python
"""Standalone CLI for validating comic script JSONs.

Usage:
    python -m tk_comfyui_batch_image.validate <file1> [file2 ...] [options]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core.validator import CheckError, collect_errors


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize_file(path: Path, data: dict) -> dict:
    pages = data.get("pages", [])
    return {
        "job_id": data.get("job_id"),
        "page_count": len(pages),
        "panel_count": sum(len(p.get("panels", [])) for p in pages),
    }


def _format_human_errors(errors: list[CheckError]) -> str:
    blocks = []
    for e in errors:
        lines = [f"  [L{e.layer}] {e.path}", f"    {e.message}"]
        if e.hint:
            lines.append(f"    hint: {e.hint}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _print_file_human(path: Path, status: str, errors: list[CheckError], info: dict | None):
    if status == "ok":
        print(f"✓ {path}")
        if info:
            print(f"  version {info.get('version', '?')}, "
                  f"{info['page_count']} pages, {info['panel_count']} panels, "
                  f"job_id={info['job_id']}")
    else:
        print(f"✗ {path}  ({len(errors)} errors)")
        print()
        print(_format_human_errors(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tk_comfyui_batch_image.validate",
        description="Validate comic script JSON(s).",
    )
    parser.add_argument("files", nargs="*", help="JSON file(s) to validate")
    args = parser.parse_args(argv)

    if not args.files:
        parser.print_usage(sys.stderr)
        return 2

    any_fail = False

    for raw in args.files:
        path = Path(raw)
        if not path.exists():
            print(f"✗ {path}  (file not found)", file=sys.stderr)
            any_fail = True
            return 3
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError) as e:
            print(f"✗ {path}  (I/O or JSON parse error: {e})", file=sys.stderr)
            return 3

        errors = collect_errors(data)
        if errors:
            any_fail = True
            _print_file_human(path, "fail", errors, None)
        else:
            info = {"version": data.get("version"), **_summarize_file(path, data)}
            _print_file_human(path, "ok", [], info)

    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Also create `tk_comfyui_batch_image/__main__.py`? No — the CLI uses `python -m tk_comfyui_batch_image.validate`, so Python's `-m` runs `tk_comfyui_batch_image/validate.py` directly via its `if __name__ == "__main__"` block. No extra file needed.

- [ ] **Step 4: Run CLI tests — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_cli_validate.py -v`
Expected: 5 passed.

- [ ] **Step 5: Smoke-test the CLI manually**

Run:

```bash
python -m tk_comfyui_batch_image.validate tk_comfyui_batch_image/tests/fixtures/scripts/basic.json
```

Expected: `✓ tk_comfyui_batch_image/tests/fixtures/scripts/basic.json` followed by the version/page/panel/job_id summary line, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/validate.py tk_comfyui_batch_image/tests/test_cli_validate.py
git commit -m "feat(cli): validate entrypoint with exit codes + human output"
```

---

## Task 9: CLI — `--json` output mode

**Files:**
- Modify: `tk_comfyui_batch_image/validate.py`
- Test: `tk_comfyui_batch_image/tests/test_cli_validate.py`

- [ ] **Step 1: Write the failing tests**

Append to `tk_comfyui_batch_image/tests/test_cli_validate.py`:

```python
def test_cli_json_output_structure_on_success(tmp_path, capsys):
    p = _write(tmp_path, "ok.json", _valid_minimal_book())
    code = main([str(p), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["summary"] == {"total": 1, "ok": 1, "fail": 0}
    assert len(payload["files"]) == 1
    f0 = payload["files"][0]
    assert f0["status"] == "ok"
    assert f0["errors"] == []
    assert f0["info"]["job_id"] == "cli_test"
    assert f0["info"]["page_count"] == 1
    assert f0["info"]["panel_count"] == 1


def test_cli_json_output_structure_on_failure(tmp_path, capsys):
    book = _valid_minimal_book()
    book["pages"][0]["page_index"] = 5
    p = _write(tmp_path, "bad.json", book)
    code = main([str(p), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["summary"] == {"total": 1, "ok": 0, "fail": 1}
    f0 = payload["files"][0]
    assert f0["status"] == "fail"
    assert len(f0["errors"]) >= 1
    err = f0["errors"][0]
    assert err["layer"] == 2
    assert err["path"] == "pages[0].page_index"
    assert "expected 1" in err["message"]
```

- [ ] **Step 2: Run tests — fail**

Run: `pytest tk_comfyui_batch_image/tests/test_cli_validate.py -k json -v`
Expected: 2 FAIL (`--json` not recognised / no JSON output).

- [ ] **Step 3: Add --json to CLI**

In `tk_comfyui_batch_image/validate.py`:

3a. Add the `asdict` import to the top of `validate.py` (alongside the existing imports):

```python
from dataclasses import asdict
```

Place it between `import sys` and `from pathlib import Path` so the stdlib imports stay grouped alphabetically.

3b. Add `--json` to the parser (inside `main()` after the existing `parser.add_argument("files" ...)`):

```python
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of human-readable text")
```

3c. Add this helper above `main()` (below `_print_file_human`):

```python
def _file_result_dict(path: Path, status: str, errors: list[CheckError], info: dict | None) -> dict:
    d = {
        "path": str(path),
        "status": status,
        "errors": [asdict(e) for e in errors],
    }
    if info is not None:
        d["info"] = info
    return d
```

3d. Replace the per-file `for raw in args.files:` loop so that results accumulate and are either printed incrementally (human mode) or emitted once at the end (JSON mode):

```python
    results: list[dict] = []
    any_fail = False
    for raw in args.files:
        path = Path(raw)
        if not path.exists():
            if args.json:
                results.append({"path": str(path), "status": "fail",
                                "errors": [{"layer": 0, "path": "<io>",
                                            "message": "file not found", "hint": None}]})
                any_fail = True
                continue
            else:
                print(f"✗ {path}  (file not found)", file=sys.stderr)
                return 3
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError) as e:
            if args.json:
                results.append({"path": str(path), "status": "fail",
                                "errors": [{"layer": 0, "path": "<io>",
                                            "message": f"I/O or JSON parse error: {e}",
                                            "hint": None}]})
                any_fail = True
                continue
            else:
                print(f"✗ {path}  (I/O or JSON parse error: {e})", file=sys.stderr)
                return 3

        errors = collect_errors(data)
        if errors:
            any_fail = True
            if args.json:
                results.append(_file_result_dict(path, "fail", errors, None))
            else:
                _print_file_human(path, "fail", errors, None)
        else:
            info = {"version": data.get("version"), **_summarize_file(path, data)}
            if args.json:
                results.append(_file_result_dict(path, "ok", [], info))
            else:
                _print_file_human(path, "ok", [], info)

    if args.json:
        summary = {
            "total": len(results),
            "ok":   sum(1 for r in results if r["status"] == "ok"),
            "fail": sum(1 for r in results if r["status"] == "fail"),
        }
        print(json.dumps({"summary": summary, "files": results},
                         indent=2, ensure_ascii=False))

    return 1 if any_fail else 0
```

Note: in JSON mode, I/O errors become layer=0 entries in the results array rather than process-level exit 3 — this keeps the output schema uniform so AI can handle a mixed batch. The exit code for JSON mode is still 1 (any_fail) not 3. If the user wants exit 3 for I/O, they should run without --json.

- [ ] **Step 4: Run JSON tests — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_cli_validate.py -k json -v`
Expected: 2 passed.

- [ ] **Step 5: Run the full CLI test file**

Run: `pytest tk_comfyui_batch_image/tests/test_cli_validate.py -v`
Expected: 7 passed total.

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/validate.py tk_comfyui_batch_image/tests/test_cli_validate.py
git commit -m "feat(cli): --json machine-readable output mode"
```

---

## Task 10: CLI — multi-file + `--max-errors` truncation

**Files:**
- Modify: `tk_comfyui_batch_image/validate.py`
- Test: `tk_comfyui_batch_image/tests/test_cli_validate.py`

- [ ] **Step 1: Write the failing tests**

Append to `tk_comfyui_batch_image/tests/test_cli_validate.py`:

```python
def test_cli_multi_file_mixed_exits_1_with_summary(tmp_path, capsys):
    ok = _write(tmp_path, "ok.json", _valid_minimal_book())
    bad_book = _valid_minimal_book()
    bad_book["pages"][0]["page_index"] = 5
    bad = _write(tmp_path, "bad.json", bad_book)
    code = main([str(ok), str(bad)])
    out = capsys.readouterr().out
    assert code == 1
    assert "✓" in out and "✗" in out
    assert "Summary" in out
    assert "2 files" in out
    assert "1 ✓" in out and "1 ✗" in out


def test_cli_max_errors_truncates_human(tmp_path, capsys):
    book = _valid_minimal_book()
    # Create 10 page_index gaps (a gap per page).
    panel_template = book["pages"][0]["panels"][0]
    book["pages"] = [{
        "page_index": 100 + i,
        "page_prompt": {"positive": "", "negative": ""},
        "layout_mode": "vertical_stack",
        "panels": [{**panel_template, "panel_index": 1, "height_px": 100}],
    } for i in range(10)]
    p = _write(tmp_path, "many.json", book)
    code = main([str(p), "--max-errors", "3"])
    out = capsys.readouterr().out
    assert code == 1
    assert out.count("[L2]") == 3
    assert "7 more error" in out   # e.g. "... and 7 more errors suppressed"


def test_cli_max_errors_truncated_flag_in_json(tmp_path, capsys):
    book = _valid_minimal_book()
    panel_template = book["pages"][0]["panels"][0]
    book["pages"] = [{
        "page_index": 100 + i,
        "page_prompt": {"positive": "", "negative": ""},
        "layout_mode": "vertical_stack",
        "panels": [{**panel_template, "panel_index": 1, "height_px": 100}],
    } for i in range(5)]
    p = _write(tmp_path, "many.json", book)
    code = main([str(p), "--json", "--max-errors", "2"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    f0 = payload["files"][0]
    assert len(f0["errors"]) == 2
    assert f0["truncated"] is True
```

- [ ] **Step 2: Run tests — fail**

Run: `pytest tk_comfyui_batch_image/tests/test_cli_validate.py -v`
Expected: 3 new tests FAIL.

- [ ] **Step 3: Add --max-errors + truncation + multi-file summary**

In `tk_comfyui_batch_image/validate.py`:

3a. Add the flag in the parser:

```python
    parser.add_argument("--max-errors", type=int, default=20, metavar="N",
                        help="Show at most N errors per file (default: 20)")
```

3b. Update `_file_result_dict` to accept truncation info:

```python
def _file_result_dict(path: Path, status: str, errors: list[CheckError],
                      info: dict | None, truncated: bool = False) -> dict:
    d = {
        "path": str(path),
        "status": status,
        "errors": [asdict(e) for e in errors],
        "truncated": truncated,
    }
    if info is not None:
        d["info"] = info
    return d
```

3c. Update `_print_file_human` to accept and show truncation:

```python
def _print_file_human(path: Path, status: str, errors: list[CheckError],
                      info: dict | None, suppressed: int = 0):
    if status == "ok":
        print(f"✓ {path}")
        if info:
            print(f"  version {info.get('version', '?')}, "
                  f"{info['page_count']} pages, {info['panel_count']} panels, "
                  f"job_id={info['job_id']}")
    else:
        total = len(errors) + suppressed
        print(f"✗ {path}  ({total} errors)")
        print()
        print(_format_human_errors(errors))
        if suppressed > 0:
            print()
            print(f"  ... and {suppressed} more error(s) suppressed "
                  f"(raise --max-errors to see all)")
```

3d. Update the per-file fail branches in `main()` to apply truncation:

Replace:

```python
        errors = collect_errors(data)
        if errors:
            any_fail = True
            if args.json:
                results.append(_file_result_dict(path, "fail", errors, None))
            else:
                _print_file_human(path, "fail", errors, None)
```

with:

```python
        errors = collect_errors(data)
        if errors:
            any_fail = True
            shown = errors[:args.max_errors]
            suppressed = max(0, len(errors) - args.max_errors)
            truncated = suppressed > 0
            if args.json:
                results.append(_file_result_dict(path, "fail", shown, None, truncated))
            else:
                _print_file_human(path, "fail", shown, None, suppressed)
```

3e. Add the multi-file human summary. At the very end of `main()`, just before `return 1 if any_fail else 0`, insert:

```python
    if not args.json and len(args.files) > 1:
        total = len(args.files)
        ok_count = total - sum(1 for f in args.files
                               if not Path(f).exists() or _result_failed(f))
        # Simpler recount: use tracked any_fail + per-file results not retained in human mode.
        # Instead track counts inside the loop — patched in.
```

On second thought, the cleanest pattern is to track counts directly. Replace the entire `main()` body with a version that keeps per-file status counts:

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tk_comfyui_batch_image.validate",
        description="Validate comic script JSON(s).",
    )
    parser.add_argument("files", nargs="*", help="JSON file(s) to validate")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of human-readable text")
    parser.add_argument("--max-errors", type=int, default=20, metavar="N",
                        help="Show at most N errors per file (default: 20)")
    args = parser.parse_args(argv)

    if not args.files:
        parser.print_usage(sys.stderr)
        return 2

    results: list[dict] = []
    ok_count = 0
    fail_count = 0

    for raw in args.files:
        path = Path(raw)

        if not path.exists():
            if args.json:
                results.append(_file_result_dict(
                    path, "fail",
                    [CheckError(layer=0, path="<io>", message="file not found")],
                    None, False,
                ))
                fail_count += 1
                continue
            print(f"✗ {path}  (file not found)", file=sys.stderr)
            return 3

        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError) as e:
            if args.json:
                results.append(_file_result_dict(
                    path, "fail",
                    [CheckError(layer=0, path="<io>",
                                message=f"I/O or JSON parse error: {e}")],
                    None, False,
                ))
                fail_count += 1
                continue
            print(f"✗ {path}  (I/O or JSON parse error: {e})", file=sys.stderr)
            return 3

        errors = collect_errors(data)
        if errors:
            fail_count += 1
            shown = errors[:args.max_errors]
            suppressed = max(0, len(errors) - args.max_errors)
            truncated = suppressed > 0
            if args.json:
                results.append(_file_result_dict(path, "fail", shown, None, truncated))
            else:
                _print_file_human(path, "fail", shown, None, suppressed)
        else:
            ok_count += 1
            info = {"version": data.get("version"), **_summarize_file(path, data)}
            if args.json:
                results.append(_file_result_dict(path, "ok", [], info, False))
            else:
                _print_file_human(path, "ok", [], info)

    if args.json:
        print(json.dumps({
            "summary": {"total": ok_count + fail_count,
                        "ok": ok_count, "fail": fail_count},
            "files": results,
        }, indent=2, ensure_ascii=False))
    elif len(args.files) > 1:
        print()
        print("---")
        total = ok_count + fail_count
        print(f"Summary: {total} files, {ok_count} ✓ ok, {fail_count} ✗ fail")

    return 1 if fail_count > 0 else 0
```

Delete the `_result_failed` reference (it was never added).

- [ ] **Step 4: Run the full CLI test file**

Run: `pytest tk_comfyui_batch_image/tests/test_cli_validate.py -v`
Expected: 10 passed.

- [ ] **Step 5: Run the whole project suite**

Run: `pytest tk_comfyui_batch_image/tests/ -q && ruff check tk_comfyui_batch_image`
Expected: all pass, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/validate.py tk_comfyui_batch_image/tests/test_cli_validate.py
git commit -m "feat(cli): multi-file summary + --max-errors truncation"
```

---

## Task 11: schema_export + drift test

**Files:**
- Create: `tk_comfyui_batch_image/schema_export.py`
- Create: `docs/skills/comic-script-authoring/schema.json` (generated)
- Create: `tk_comfyui_batch_image/tests/test_schema_export.py`

- [ ] **Step 1: Write the failing drift test**

Create `tk_comfyui_batch_image/tests/test_schema_export.py`:

```python
"""Ensure the exported schema.json stays in sync with core/schema.COMIC_SCHEMA."""
import json

from tk_comfyui_batch_image.core.schema import COMIC_SCHEMA
from tk_comfyui_batch_image.schema_export import SCHEMA_JSON_PATH, export_schema


def test_schema_json_matches_core_schema():
    """If this fails, run `python -m tk_comfyui_batch_image.schema_export`."""
    expected = COMIC_SCHEMA
    on_disk = json.loads(SCHEMA_JSON_PATH.read_text(encoding="utf-8"))
    assert on_disk == expected


def test_export_schema_writes_valid_json(tmp_path, monkeypatch):
    """Exporting to a custom path round-trips cleanly."""
    out = tmp_path / "schema.json"
    export_schema(out)
    round_trip = json.loads(out.read_text(encoding="utf-8"))
    assert round_trip == COMIC_SCHEMA
```

- [ ] **Step 2: Run the test — fail**

Run: `pytest tk_comfyui_batch_image/tests/test_schema_export.py -v`
Expected: ImportError on `tk_comfyui_batch_image.schema_export`.

- [ ] **Step 3: Implement the exporter**

Create `tk_comfyui_batch_image/schema_export.py`:

```python
"""Export core/schema.COMIC_SCHEMA to the skill pack's schema.json.

Run as a module:
    python -m tk_comfyui_batch_image.schema_export
"""
from __future__ import annotations

import json
from pathlib import Path

from .core.schema import COMIC_SCHEMA

SCHEMA_JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs" / "skills" / "comic-script-authoring" / "schema.json"
)


def export_schema(out_path: Path | None = None) -> Path:
    target = out_path or SCHEMA_JSON_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(COMIC_SCHEMA, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


if __name__ == "__main__":
    written = export_schema()
    print(f"Wrote {written}")
```

- [ ] **Step 4: Generate the initial schema.json**

Run: `python -m tk_comfyui_batch_image.schema_export`
Expected: prints `Wrote .../docs/skills/comic-script-authoring/schema.json`.

Verify file exists:

```bash
ls docs/skills/comic-script-authoring/schema.json
```

- [ ] **Step 5: Run the drift test — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_schema_export.py -v`
Expected: 2 passed.

- [ ] **Step 6: Run the full suite**

Run: `pytest tk_comfyui_batch_image/tests/ -q`
Expected: all pass (now 106 tests: 94 + 7 CLI + 3 JSON + 2 schema).

Hmm, arithmetic: 94 (Task 6 end) + 5 CLI in Task 8 + 2 in Task 9 + 3 in Task 10 + 2 in Task 11 = 106. Good.

- [ ] **Step 7: Commit**

```bash
git add tk_comfyui_batch_image/schema_export.py tk_comfyui_batch_image/tests/test_schema_export.py docs/skills/comic-script-authoring/schema.json
git commit -m "feat(schema): export COMIC_SCHEMA to skill pack schema.json + drift test"
```

---

## Task 12: Example 01 (minimal) + parametric regression test

**Files:**
- Create: `docs/skills/comic-script-authoring/examples/01_minimal/screenplay.md`
- Create: `docs/skills/comic-script-authoring/examples/01_minimal/output.json`
- Create: `tk_comfyui_batch_image/tests/test_examples_valid.py`

- [ ] **Step 1: Write the failing parametric regression test**

Create `tk_comfyui_batch_image/tests/test_examples_valid.py`:

```python
"""Each example's output.json must pass the M2 validator."""
import json
from pathlib import Path

import pytest

from tk_comfyui_batch_image.core.validator import validate

EXAMPLES_ROOT = (
    Path(__file__).resolve().parent.parent.parent
    / "docs" / "skills" / "comic-script-authoring" / "examples"
)


def _example_dirs():
    if not EXAMPLES_ROOT.exists():
        return []
    return sorted(d for d in EXAMPLES_ROOT.iterdir() if d.is_dir())


@pytest.mark.parametrize("example_dir", _example_dirs(), ids=lambda d: d.name)
def test_example_output_json_is_valid(example_dir):
    output = example_dir / "output.json"
    assert output.exists(), f"{example_dir.name} is missing output.json"
    data = json.loads(output.read_text(encoding="utf-8"))
    validate(data)   # raises ValidationError if bad


@pytest.mark.parametrize("example_dir", _example_dirs(), ids=lambda d: d.name)
def test_example_has_screenplay(example_dir):
    screenplay = example_dir / "screenplay.md"
    assert screenplay.exists(), f"{example_dir.name} is missing screenplay.md"
    assert screenplay.read_text(encoding="utf-8").strip(), \
        f"{example_dir.name}/screenplay.md is empty"
```

- [ ] **Step 2: Run the test — 0 params initially**

Run: `pytest tk_comfyui_batch_image/tests/test_examples_valid.py -v`
Expected: 0 tests collected (parametrize list is empty because examples dir doesn't exist yet). pytest exits 5 (no tests collected). That's fine — it'll auto-collect once we add examples.

- [ ] **Step 3: Write example 01 screenplay.md**

Create `docs/skills/comic-script-authoring/examples/01_minimal/screenplay.md`:

```markdown
# Example 01 — Minimal

## Target
Teach the absolute-minimum JSON: one page, one panel, default canvas (1080×1920).

## Screenplay

主角站在窗前看雨。

## Expected AI reasoning

- No reading direction specified → default `ltr`
- No page size specified → use default 1080×1920 + `page_template="custom"`
- One scene → one page, one panel
- No emotional cue → medium-size panel (height ~600px, full width ~1040px)
- Character appearance not described → keep `character_prompt` minimal / empty
```

- [ ] **Step 4: Write example 01 output.json**

Create `docs/skills/comic-script-authoring/examples/01_minimal/output.json`:

```json
{
  "version": "1.0",
  "job_id": "example_01_minimal",
  "reading_direction": "ltr",
  "page_template": "custom",
  "page_width_px": 1080,
  "page_height_px": 1920,
  "bleed_px": 20,
  "gutter_px": 10,
  "page_background": "#FFFFFF",
  "base_seed": 1,
  "style_prompt":     { "positive": "manga style, clean linework", "negative": "blurry, low quality" },
  "character_prompt": { "positive": "", "negative": "" },
  "default_sampler":  { "sampler_name": "euler", "scheduler": "normal", "steps": 25, "cfg": 7.0, "denoise": 1.0 },
  "default_border":   { "width_px": 2, "color": "#000000", "style": "solid" },
  "pages": [
    {
      "page_index": 1,
      "page_prompt": { "positive": "", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        {
          "panel_index": 1,
          "scene_prompt": { "positive": "a protagonist stands by a window, watching rain", "negative": "" },
          "width_px": 1040,
          "height_px": 600,
          "align": "center",
          "shape": { "type": "rect" }
        }
      ]
    }
  ]
}
```

- [ ] **Step 5: Run the parametric test — pass**

Run: `pytest tk_comfyui_batch_image/tests/test_examples_valid.py -v`
Expected: 2 passed (one per parametrize × test function).

- [ ] **Step 6: Smoke-test via CLI**

Run: `python -m tk_comfyui_batch_image.validate docs/skills/comic-script-authoring/examples/01_minimal/output.json`
Expected: `✓ ...01_minimal/output.json` followed by `version 1.0, 1 pages, 1 panels, job_id=example_01_minimal`, exit 0.

- [ ] **Step 7: Commit**

```bash
git add docs/skills/comic-script-authoring/examples/01_minimal tk_comfyui_batch_image/tests/test_examples_valid.py
git commit -m "feat(skill-pack): example 01 minimal + parametric regression test"
```

---

## Task 13: Examples 02–05

**Files:**
- Create: 4 pairs of `screenplay.md` + `output.json` under `docs/skills/comic-script-authoring/examples/`

- [ ] **Step 1: Write example 02 (vertical_stack + align) screenplay.md**

Create `docs/skills/comic-script-authoring/examples/02_vertical_stack_3panel/screenplay.md`:

```markdown
# Example 02 — vertical_stack with align

## Target
Teach three stacked panels using `layout_mode=vertical_stack` with varied `align`.

## Screenplay

第一格：清晨街景（建立場景，重要）。
第二格：主角推開門走出公寓，動作連續。
第三格：路人經過，主角驚訝看向他（情緒轉折）。

## Expected AI reasoning

- 3 scenes → 3 panels, all rectangles on one page
- Panel 1 (establishing) → large, center-aligned
- Panel 2 (action beat) → medium, left-aligned
- Panel 3 (emotion) → large, right-aligned to vary rhythm
- All panels share width ≤ 1040 (page_width 1080 - bleed 20*2)
- Total heights + 2 gutters must fit inside inner 1880 (= 1920 - 20*2)
```

- [ ] **Step 2: Write example 02 output.json**

Create `docs/skills/comic-script-authoring/examples/02_vertical_stack_3panel/output.json`:

```json
{
  "version": "1.0",
  "job_id": "example_02_stack",
  "reading_direction": "ltr",
  "page_template": "custom",
  "page_width_px": 1080,
  "page_height_px": 1920,
  "bleed_px": 20,
  "gutter_px": 20,
  "page_background": "#FFFFFF",
  "base_seed": 2,
  "style_prompt":     { "positive": "manga style, clean linework", "negative": "blurry" },
  "character_prompt": { "positive": "young man, short hair, casual clothes", "negative": "" },
  "default_sampler":  { "sampler_name": "euler", "scheduler": "normal", "steps": 25, "cfg": 7.0, "denoise": 1.0 },
  "default_border":   { "width_px": 2, "color": "#000000", "style": "solid" },
  "pages": [
    {
      "page_index": 1,
      "page_prompt": { "positive": "morning street, soft light", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        {
          "panel_index": 1,
          "scene_prompt": { "positive": "establishing shot of a quiet morning street, soft sunlight", "negative": "" },
          "width_px": 1040, "height_px": 800,
          "align": "center", "shape": { "type": "rect" }
        },
        {
          "panel_index": 2,
          "scene_prompt": { "positive": "young man stepping out of an apartment door", "negative": "" },
          "width_px": 1000, "height_px": 400,
          "align": "left", "shape": { "type": "rect" }
        },
        {
          "panel_index": 3,
          "scene_prompt": { "positive": "young man turning with surprise as a passerby walks by", "negative": "" },
          "width_px": 1040, "height_px": 620,
          "align": "right", "shape": { "type": "rect" }
        }
      ]
    }
  ]
}
```

Note: 800 + 400 + 620 = 1820 + 2 gutters × 20 = 40 → total 1860 ≤ inner 1880 ✓.

- [ ] **Step 3: Write example 03 (per-panel sampler_override) screenplay.md**

Create `docs/skills/comic-script-authoring/examples/03_per_panel_override/screenplay.md`:

```markdown
# Example 03 — per-panel sampler_override

## Target
Teach `sampler_override` for panels that need higher quality.

## Screenplay

一頁兩格。第一格是輕鬆的過場。
第二格是整個故事的封面級高潮畫面，要非常精緻，多花些 steps。

## Expected AI reasoning

- Panel 2 is explicitly a "cover-level" shot → bump steps + cfg via sampler_override
- Panel 1 stays on default_sampler
- Heights chosen so the climactic panel is larger (e.g. 1100 vs 600)
- Both use rect (M1 limit)
```

- [ ] **Step 4: Write example 03 output.json**

Create `docs/skills/comic-script-authoring/examples/03_per_panel_override/output.json`:

```json
{
  "version": "1.0",
  "job_id": "example_03_override",
  "reading_direction": "ltr",
  "page_template": "custom",
  "page_width_px": 1080,
  "page_height_px": 1920,
  "bleed_px": 20,
  "gutter_px": 20,
  "page_background": "#FFFFFF",
  "base_seed": 3,
  "style_prompt":     { "positive": "manga style", "negative": "blurry" },
  "character_prompt": { "positive": "heroine, long hair", "negative": "" },
  "default_sampler":  { "sampler_name": "euler", "scheduler": "normal", "steps": 25, "cfg": 7.0, "denoise": 1.0 },
  "default_border":   { "width_px": 2, "color": "#000000", "style": "solid" },
  "pages": [
    {
      "page_index": 1,
      "page_prompt": { "positive": "", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        {
          "panel_index": 1,
          "scene_prompt": { "positive": "transition shot, mundane corridor", "negative": "" },
          "width_px": 1040, "height_px": 600,
          "align": "center", "shape": { "type": "rect" }
        },
        {
          "panel_index": 2,
          "scene_prompt": { "positive": "cover-worthy heroic pose, dramatic lighting, intricate background", "negative": "low detail" },
          "width_px": 1040, "height_px": 1100,
          "align": "center", "shape": { "type": "rect" },
          "sampler_override": { "steps": 60, "cfg": 8.5 }
        }
      ]
    }
  ]
}
```

Note: 600 + 1100 + 20 (gutter) = 1720 ≤ 1880 ✓.

- [ ] **Step 5: Write example 04 (reading_direction=rtl) screenplay.md**

Create `docs/skills/comic-script-authoring/examples/04_rtl_reading/screenplay.md`:

```markdown
# Example 04 — reading_direction = rtl

## Target
Japanese-style manga default: rtl reading direction.

## Screenplay

這是一段短篇日式漫畫。主角走進神社（第一格），
蹲下抽一支籤（第二格），看到籤上的字（第三格，情緒重點，放大）。

## Expected AI reasoning

- Culture cue "神社 / 籤" → Japanese → set `reading_direction: "rtl"`
- 3 panels
- Panel 3 is emotional peak → largest height
- Still all rect (M1)
```

- [ ] **Step 6: Write example 04 output.json**

Create `docs/skills/comic-script-authoring/examples/04_rtl_reading/output.json`:

```json
{
  "version": "1.0",
  "job_id": "example_04_rtl",
  "reading_direction": "rtl",
  "page_template": "custom",
  "page_width_px": 1080,
  "page_height_px": 1920,
  "bleed_px": 20,
  "gutter_px": 20,
  "page_background": "#FFFFFF",
  "base_seed": 4,
  "style_prompt":     { "positive": "japanese manga, ink, screentone", "negative": "color, realistic" },
  "character_prompt": { "positive": "teenage girl, school uniform", "negative": "" },
  "default_sampler":  { "sampler_name": "euler", "scheduler": "normal", "steps": 25, "cfg": 7.0, "denoise": 1.0 },
  "default_border":   { "width_px": 2, "color": "#000000", "style": "solid" },
  "pages": [
    {
      "page_index": 1,
      "page_prompt": { "positive": "shrine, tranquil", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        {
          "panel_index": 1,
          "scene_prompt": { "positive": "a teenage girl walking into a shrine gate", "negative": "" },
          "width_px": 1040, "height_px": 500,
          "align": "center", "shape": { "type": "rect" }
        },
        {
          "panel_index": 2,
          "scene_prompt": { "positive": "the girl kneeling to draw a fortune strip", "negative": "" },
          "width_px": 1040, "height_px": 400,
          "align": "center", "shape": { "type": "rect" }
        },
        {
          "panel_index": 3,
          "scene_prompt": { "positive": "close-up on fortune paper, kanji clearly visible, dramatic", "negative": "" },
          "width_px": 1040, "height_px": 940,
          "align": "center", "shape": { "type": "rect" }
        }
      ]
    }
  ]
}
```

Note: 500 + 400 + 940 + 2×20 = 1880 = inner 1880 ✓ (edge case).

- [ ] **Step 7: Write example 05 (character_prompt + 4-layer style) screenplay.md**

Create `docs/skills/comic-script-authoring/examples/05_character_prompt_style/screenplay.md`:

```markdown
# Example 05 — 4-layer prompt stacking

## Target
Show how style_prompt + character_prompt + page_prompt + scene_prompt compose.
Two pages with the same main character across multiple environments.

## Screenplay

主角是一名黑髮藍眼的少年騎士。
第一頁：他站在城堡中庭練劍（兩格：全景 + 動作特寫）。
第二頁：他走到高塔頂端俯瞰王國（一格，壯闊）。

## Expected AI reasoning

- Character appears across all panels → put fixed description in character_prompt
- style_prompt carries the overall art style
- page_prompt carries per-page environmental mood
- scene_prompt carries the specific action/shot
- Page 2 uses a single tall panel (800 or larger) for the sweeping vista
- All rect (M1)
```

- [ ] **Step 8: Write example 05 output.json**

Create `docs/skills/comic-script-authoring/examples/05_character_prompt_style/output.json`:

```json
{
  "version": "1.0",
  "job_id": "example_05_layers",
  "reading_direction": "ltr",
  "page_template": "custom",
  "page_width_px": 1080,
  "page_height_px": 1920,
  "bleed_px": 20,
  "gutter_px": 20,
  "page_background": "#FFFFFF",
  "base_seed": 5,
  "style_prompt":     { "positive": "high-detail manga, clean inks, fantasy art", "negative": "photo, 3d render" },
  "character_prompt": { "positive": "a young knight, black hair, blue eyes, silver armor", "negative": "elderly, wrong hair color" },
  "default_sampler":  { "sampler_name": "euler", "scheduler": "normal", "steps": 25, "cfg": 7.0, "denoise": 1.0 },
  "default_border":   { "width_px": 2, "color": "#000000", "style": "solid" },
  "pages": [
    {
      "page_index": 1,
      "page_prompt": { "positive": "castle courtyard, morning", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        {
          "panel_index": 1,
          "scene_prompt": { "positive": "wide establishing shot of the courtyard with the knight in the center practicing", "negative": "" },
          "width_px": 1040, "height_px": 900,
          "align": "center", "shape": { "type": "rect" }
        },
        {
          "panel_index": 2,
          "scene_prompt": { "positive": "close-up of the knight mid-swing, focused expression", "negative": "" },
          "width_px": 1040, "height_px": 960,
          "align": "center", "shape": { "type": "rect" }
        }
      ]
    },
    {
      "page_index": 2,
      "page_prompt": { "positive": "high tower, vast kingdom view, sunset", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        {
          "panel_index": 1,
          "scene_prompt": { "positive": "the knight standing at the tower battlement, overlooking a sprawling kingdom", "negative": "" },
          "width_px": 1040, "height_px": 1700,
          "align": "center", "shape": { "type": "rect" }
        }
      ]
    }
  ]
}
```

Note: Page 1: 900+960+20 = 1880 ≤ 1880 ✓. Page 2: 1700 ≤ 1880 ✓.

- [ ] **Step 9: Run the examples regression**

Run: `pytest tk_comfyui_batch_image/tests/test_examples_valid.py -v`
Expected: 10 passed (5 examples × 2 test functions).

- [ ] **Step 10: Run the full suite**

Run: `pytest tk_comfyui_batch_image/tests/ -q && ruff check tk_comfyui_batch_image`
Expected: all green. Total tests ≈ 116.

- [ ] **Step 11: Smoke-test via CLI**

Run: `python -m tk_comfyui_batch_image.validate docs/skills/comic-script-authoring/examples/*/output.json`
Expected: 5 × `✓` lines, summary `Summary: 5 files, 5 ✓ ok, 0 ✗ fail`, exit 0.

- [ ] **Step 12: Commit**

```bash
git add docs/skills/comic-script-authoring/examples
git commit -m "feat(skill-pack): examples 02–05 covering align, override, rtl, 4-layer prompts"
```

---

## Task 14: SKILL.md

**Files:**
- Create: `docs/skills/comic-script-authoring/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `docs/skills/comic-script-authoring/SKILL.md`:

```markdown
---
name: comic-script-authoring
description: Use this skill when the user provides a natural-language screenplay and asks for a comic panel JSON, storyboard JSON, or output that feeds tk_comfyui_batch_image. You act as a manga panel composition expert (分鏡師) and produce JSON that passes the tk_comfyui_batch_image validator.
---

# Comic Script Authoring

You are a professional manga panel composition artist (分鏡師).
Your job: read a natural-language screenplay and output a JSON the
`tk_comfyui_batch_image` ComfyUI node can execute.

## Process

1. **Read the whole screenplay before writing anything.**
2. **Book-level constants first:**
   - `reading_direction` — cultural cue (Japanese story → `rtl`, Western → `ltr`)
   - `style_prompt` — one art style for the whole book
   - `character_prompt` — fixed appearance of recurring characters
   - `default_sampler` and `default_border` — use sane defaults if the user didn't specify
3. **Per scene, decide:**
   - New page or continue current page?
   - Panel height (use the size table below)
   - `scene_prompt` — what's actually drawn
4. **Output the JSON draft.**
5. **Run the self-check loop (below).**
6. **Deliver only after the loop exits 0.**

## Default canvas (when the user does NOT specify)

- `page_template`: `"custom"`
- `page_width_px`: `1080`
- `page_height_px`: `1920`

Portrait digital comic (Instagram Story / phone-screen proportions). This is the
baseline for "big / small" panel judgements below.

## Panel size table (calibrated for 1080×1920 — scale proportionally for other sizes)

| Class | height_px range | % of page height | When |
|---|---|---|---|
| Extra-large | 1200–1700 | 60–90% | Emotional peak, reveal, cover-grade |
| Large | 800–1200 | 40–60% | Important scene, highlight |
| Medium | 500–800 | 25–40% | General narrative beat |
| Small | 300–500 | 15–25% | Reaction shot, fast beat |
| Tiny | <300 | <15% | Detail, micro-beat |

Panel width is usually the full inner page width (`page_width_px - bleed_px*2`).
Only shrink width for deliberate off-center compositions using `align`.

## Panels per page (guidance)

- Standard pacing: 2–4 panels
- Fast beats: 5–6
- High-emotion / slow: 1–2 (prefer large)
- More than 6: consider splitting into a new page unless chaos is the intent

## Composition principles (apply when the user didn't specify)

- Emotional peak / reveal → large panel
- Reaction / beat → small stacked panels
- Establishing shot (new location) → first panel, medium-to-large
- Dialog shot-reverse-shot → two stacked rectangles (M1 has no side-by-side layout yet)
- `rtl` suits Japanese content; `ltr` suits Western

## Absolute prohibitions

- Do NOT invent fields outside the schema.
- Do NOT rename keys to any language (no `頁面=`, no `page_宽`).
- `shape.type` MUST be `"rect"` (this release does not support `split` / `polygon`).
- `layout_mode` MUST be `"vertical_stack"` (other modes ship in later milestones).
- Colors MUST be `#RRGGBB` — no `rgb()`, no named colors.
- `page_template="custom"` MUST come with explicit `page_width_px` AND `page_height_px`.
- For preset templates (`A4` / `B5` / `JP_Tankobon` / `Webtoon`), do NOT also supply explicit dimensions.
- Σ panel heights + (n-1)·gutter MUST be ≤ page_height_px - bleed_px·2.
- Every panel's width MUST be ≤ page_width_px - bleed_px·2.

## Self-check loop (run EVERY time before delivering)

1. Save the draft JSON to `/tmp/draft.json` (or any path you can invoke a CLI on).
2. Run:
   ```
   python -m tk_comfyui_batch_image.validate /tmp/draft.json --json
   ```
3. Read the response:
   - `summary.fail == 0` → deliver the JSON. Done.
   - `summary.fail > 0` → for each `files[0].errors[*]`:
     - `layer == 1` → schema error (missing field, wrong type, out-of-enum). Fix per `message`.
     - `layer == 2` → semantic error. Follow `hint` verbatim.
4. Repeat step 2 until exit 0.

Do NOT deliver JSON without running the CLI. Do NOT suppress errors with JSON-style
"comments" (JSON has no comments). Do NOT skip errors; fix all of them.

## Final checklist (cross off BEFORE delivering)

- [ ] CLI exited 0?
- [ ] Every `shape.type == "rect"`?
- [ ] Every page fits (panels + gutters ≤ inner height)?
- [ ] Every panel width ≤ inner width?
- [ ] `reading_direction` matches the cultural setting?
- [ ] `character_prompt` is consistent across all panels?
- [ ] Panel sizes reflect narrative rhythm (not all identical)?

## Examples

Each directory has `screenplay.md` (input) and `output.json` (what you should produce):

- `examples/01_minimal/` — minimum required fields, default canvas
- `examples/02_vertical_stack_3panel/` — three panels with different `align`
- `examples/03_per_panel_override/` — `sampler_override` for a high-quality panel
- `examples/04_rtl_reading/` — Japanese-cued rtl reading direction
- `examples/05_character_prompt_style/` — four prompt layers composing across pages

## Schema reference

For exact field names, types, enums, and ranges, read `schema.json` (co-located with
this file). This skill deliberately does not re-list fields to avoid drift.
```

- [ ] **Step 2: Verify no tests broke**

Run: `pytest tk_comfyui_batch_image/tests/ -q`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add docs/skills/comic-script-authoring/SKILL.md
git commit -m "docs(skill-pack): SKILL.md for Claude Code + superpowers"
```

---

## Task 15: PROMPT_TEMPLATE.md and README.md

**Files:**
- Create: `docs/skills/comic-script-authoring/PROMPT_TEMPLATE.md`
- Create: `docs/skills/comic-script-authoring/README.md`

- [ ] **Step 1: Write PROMPT_TEMPLATE.md**

Create `docs/skills/comic-script-authoring/PROMPT_TEMPLATE.md`:

```markdown
# Comic Script Authoring — System Prompt Template (for generic LLMs)

Paste the text below into the system prompt of any LLM (ChatGPT, Gemini,
Claude API, etc.) that lacks shell-execution capabilities.

---

You are a professional manga panel composition artist (分鏡師).
When the user sends a natural-language screenplay, your job is to output a JSON
document that the `tk_comfyui_batch_image` ComfyUI node can execute.

## Process

1. Read the screenplay in full before drafting.
2. Pick book-level constants first: `reading_direction` (cultural cue: Japanese
   → `rtl`, Western → `ltr`), `style_prompt`, `character_prompt`,
   `default_sampler`, `default_border`.
3. For each scene decide: new page or continue, panel height class (use table
   below), and `scene_prompt` content.
4. Output JSON inside a ```json code block.
5. Ask the user to run `python -m tk_comfyui_batch_image.validate <file> --json`
   and paste the response back.
6. If `summary.fail > 0`, iterate: fix each error and re-output the FULL JSON.
7. Loop until `summary.fail == 0`.

## Default canvas (when user did not specify)

- `page_template`: `"custom"`
- `page_width_px`: `1080`
- `page_height_px`: `1920`

## Panel size table (calibrated for 1080×1920 — scale proportionally)

| Class | height_px | % of page | When |
|---|---|---|---|
| Extra-large | 1200–1700 | 60–90% | Emotional peak, reveal |
| Large | 800–1200 | 40–60% | Important scene |
| Medium | 500–800 | 25–40% | Narrative beat |
| Small | 300–500 | 15–25% | Reaction |
| Tiny | <300 | <15% | Detail |

Panel width is usually the full inner page width (`page_width_px - bleed_px*2`).

## Panels per page (guidance)

Standard 2–4, fast 5–6, emotional 1–2, never >6 without intent.

## Composition principles (apply when user did not specify)

- Emotional peak → large panel
- Reaction / beat → small stacked
- Establishing shot → first panel, medium-to-large
- Dialog shot-reverse-shot → two stacked rectangles (no side-by-side in this release)

## Absolute prohibitions

- Do NOT invent fields outside the schema.
- Do NOT rename keys to any language.
- `shape.type` MUST be `"rect"`.
- `layout_mode` MUST be `"vertical_stack"`.
- Colors MUST match `#RRGGBB`.
- `page_template="custom"` requires explicit `page_width_px` AND `page_height_px`.
- Preset `page_template` values must NOT coexist with explicit dimensions.
- Σ panel heights + (n-1)·gutter ≤ page_height_px - bleed_px·2.
- Each panel.width_px ≤ page_width_px - bleed_px·2.

## Collaboration pattern

Because you cannot run shell commands, you rely on the user to run the CLI
validator and paste results back. When you receive errors:

- For `"layer": 1` (schema): fix the field identified by `path`.
- For `"layer": 2` (semantic): follow the error `hint` literally.

Always re-emit the FULL corrected JSON inside a ```json block, never partial
diffs. The user will re-run validation.

## Schema

See `schema.json` (co-located). Fields, types, enums, ranges live there as the
single source of truth. This template deliberately does not duplicate them.
```

- [ ] **Step 2: Write README.md**

Create `docs/skills/comic-script-authoring/README.md`:

```markdown
# Comic Script Authoring Skill Pack

This directory ships everything an AI or human needs to turn a natural-language
screenplay into a JSON that drives the `tk_comfyui_batch_image` ComfyUI node.

The target audience of this README is **humans using the tool** (not AIs
producing JSON — those read `SKILL.md` or `PROMPT_TEMPLATE.md`).

## End-to-end flow

```
[You write a natural-language screenplay]
        ↓
[Your AI (Claude Code / ChatGPT / Gemini / …) reads the screenplay
 + SKILL.md or PROMPT_TEMPLATE.md]
        ↓
[AI outputs JSON]
        ↓
[AI (or you) runs `python -m tk_comfyui_batch_image.validate out.json`]
        ↓
[Drop the JSON into a ComfyUI workflow → ComicScriptLoader → ComicBatchGenerator]
        ↓
[Images]
```

## Three integration paths

### 1. Claude Code + superpowers

Copy `SKILL.md` to `~/.claude/skills/comic-script-authoring/SKILL.md` or your
project's skill directory. Then invoke it: *"Here's my screenplay — please
produce a comic JSON using the comic-script-authoring skill."*

Claude will run the self-check CLI loop automatically.

### 2. Generic LLM (ChatGPT, Gemini, Claude API, etc.)

Paste the body of `PROMPT_TEMPLATE.md` into the system prompt. Feed the
screenplay as a user message. When the model produces JSON, run the CLI
yourself and paste the response back — the model will iterate.

### 3. Programmatic pipeline

Read `schema.json` with your validator of choice in the pipeline. For CI,
`python -m tk_comfyui_batch_image.validate *.json --json` returns a
structured result you can gate on.

## Common errors

| Error | Likely cause | Fix |
|---|---|---|
| `[L2] pages[0]` total height exceeds inner | AI put too many / too tall panels on one page | Shorten a panel, or split into a new page |
| `[L1] shape.type expected "rect"` | AI tried to use `split` / `polygon` | Tell the AI the current release only supports rect |
| `[L2] root: page_template="custom" requires page_width_px` | AI omitted dimensions | Add them, or switch to a preset template |
| All panels identical size | AI did not apply composition principles | Re-prompt emphasising narrative rhythm |

## Files

- `schema.json` — generated from `tk_comfyui_batch_image/core/schema.py`. Single
  source of truth; do not hand-edit.
- `SKILL.md` — Claude Code + superpowers format.
- `PROMPT_TEMPLATE.md` — system-prompt version for generic LLMs.
- `examples/` — five `screenplay.md` / `output.json` pairs covering minimal,
  multi-panel, per-panel override, rtl reading, and 4-layer prompt composition.

## Validation CLI

```
python -m tk_comfyui_batch_image.validate <file> [more files …] [--json] [--max-errors N]
```

Exit codes: 0 = all pass, 1 = some file invalid, 2 = CLI usage error,
3 = I/O or JSON parse error.

## Feedback and extension

When a later milestone adds `shape.type="split"` (M3) or `"polygon"` (M4), the
schema will expand and new example directories will appear. The prohibitions
in `SKILL.md` / `PROMPT_TEMPLATE.md` will be relaxed accordingly. This README,
the examples list, and the error table above will be updated.
```

- [ ] **Step 3: Verify nothing broke**

Run: `pytest tk_comfyui_batch_image/tests/ -q && ruff check tk_comfyui_batch_image`
Expected: all pass, ruff clean.

- [ ] **Step 4: Run full validation on every example + self-link sanity**

Run:

```bash
python -m tk_comfyui_batch_image.validate docs/skills/comic-script-authoring/examples/*/output.json
```

Expected: 5 ✓ lines, `Summary: 5 files, 5 ✓ ok, 0 ✗ fail`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add docs/skills/comic-script-authoring/PROMPT_TEMPLATE.md docs/skills/comic-script-authoring/README.md
git commit -m "docs(skill-pack): PROMPT_TEMPLATE + README for generic LLMs and humans"
```

---

## Post-implementation verification

Once all 15 tasks have landed, run:

```bash
cd D:/tack_project/tk_comfyui_batch_image
pytest tk_comfyui_batch_image/tests/ -q
ruff check tk_comfyui_batch_image
python -m tk_comfyui_batch_image.validate docs/skills/comic-script-authoring/examples/*/output.json
python -c "import tk_comfyui_batch_image; print(sorted(tk_comfyui_batch_image.NODE_CLASS_MAPPINGS.keys()))"
```

Expected:
- `pytest`: roughly 103–120 tests pass (the exact count depends on parametric expansion; the acceptance criterion is "all green, no skipped Layer-2 tests, no xfails").
- `ruff check`: clean.
- CLI: 5 ✓, exit 0.
- Node mappings: `['ComicBatchGenerator', 'ComicPageComposer', 'ComicSamplerOverride', 'ComicScriptLoader']` (unchanged from M1 — M2 does not add nodes).

## Acceptance criteria (mirrors spec §10)

- [ ] `core/validator.py` exports `CheckError`, `collect_errors`, `validate`, and 5 Layer-2 rule functions
- [ ] `nodes/script_loader.py` calls `validate(data)`
- [ ] `validate.py` CLI: single + multi-file, `--json`, `--max-errors`, exit codes 0/1/2/3
- [ ] `schema_export.py` produces `docs/skills/comic-script-authoring/schema.json`; drift test passes
- [ ] `docs/skills/comic-script-authoring/` contains `schema.json`, `SKILL.md`, `PROMPT_TEMPLATE.md`, `README.md`, and 5 example directories
- [ ] Each example passes CLI validate (exit 0)
- [ ] `tk_comfyui_batch_image/__init__.py` unchanged (no new nodes in M2)
- [ ] Full pytest suite green, ruff clean
