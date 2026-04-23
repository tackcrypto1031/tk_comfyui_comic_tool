# M1 — Comic Batch Foundation (Rect Vertical-Stack) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a working ComfyUI node set (`ComicScriptLoader` / `ComicBatchGenerator` / `ComicPageComposer`) that takes a JSON script of rectangular panels in `vertical_stack` layout, generates each panel via KSampler, and composes the pages — end-to-end.

**Architecture:** Three ComfyUI nodes backed by pure-Python `core/` modules (schema, layout solver, prompt builder, sampler runner, cache manager, compositor). Loader validates + normalizes JSON; Generator runs an internal for-loop with panel-hash-based resume; Composer pastes panels onto a canvas with border + gutter.

**Tech Stack:** Python 3.10+, Pillow ≥ 10, jsonschema ≥ 4, numpy, torch (ComfyUI), pytest, ruff.

**Out of scope for M1 (deferred to later milestones):** `shape_group` / `polygon` shapes, anti-aliased polygon mask, standalone validator CLI, SKILL.md skill package, debug overlay, webtoon / print templates with DPI.

**Spec reference:** [`docs/superpowers/specs/2026-04-23-comfyui-comic-batch-node-design.md`](../specs/2026-04-23-comfyui-comic-batch-node-design.md)

---

## File Structure (M1)

```
tk_comfyui_batch_image/
├── __init__.py                     # ComfyUI entry — registers NODE_CLASS_MAPPINGS
├── pyproject.toml
├── README.md
├── nodes/
│   ├── __init__.py
│   ├── script_loader.py            # ComicScriptLoader
│   ├── batch_generator.py          # ComicBatchGenerator
│   └── page_composer.py            # ComicPageComposer
├── core/
│   ├── __init__.py
│   ├── types.py                    # COMIC_SCRIPT custom type name
│   ├── constants.py                # page templates, enums
│   ├── schema.py                   # M1 JSON schema (rect-only) + schema.json export
│   ├── validator.py                # jsonschema wrapper with nice error formatting
│   ├── normalizer.py               # fills defaults, resolves page_template, computes panels_solved
│   ├── prompt_builder.py           # 4-layer prompt join
│   ├── layout_solver.py            # vertical_stack rect bbox solver
│   ├── cache_manager.py            # panel hash + manifest + path helpers
│   ├── sampler_runner.py           # ComfyUI KSampler/CLIPEncode/VAEDecode wrapper
│   └── compositor.py               # rect paste + border draw
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # shared fixtures, ComfyUI stubs
│   ├── fixtures/
│   │   ├── scripts/
│   │   │   ├── minimal.json        # 1 page, 1 rect panel
│   │   │   ├── basic.json          # 2 pages, 3 panels each
│   │   │   └── invalid_missing_version.json
│   │   └── golden/                 # golden PNGs added by tests at Task 10+
│   ├── test_schema.py
│   ├── test_validator.py
│   ├── test_normalizer.py
│   ├── test_prompt_builder.py
│   ├── test_layout_solver.py
│   ├── test_cache_manager.py
│   ├── test_sampler_runner.py
│   ├── test_compositor.py
│   ├── test_script_loader.py
│   ├── test_batch_generator.py
│   ├── test_page_composer.py
│   └── test_integration_e2e.py
└── examples/
    └── workflows/
        └── m1_basic_vertical_stack.json
```

**Rationale:** `core/` is framework-free (pure Python + Pillow + numpy) so it can be tested without loading ComfyUI. `nodes/` is thin — just maps ComfyUI's typed I/O to `core/` calls. Tests import `core/` directly; nodes are tested with ComfyUI stubs from `conftest.py`.

---

## Task 1: Project skeleton & tooling

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `tk_comfyui_batch_image/__init__.py`
- Create: `tk_comfyui_batch_image/nodes/__init__.py`
- Create: `tk_comfyui_batch_image/core/__init__.py`
- Create: `tk_comfyui_batch_image/tests/__init__.py`
- Create: `.gitignore`
- Create: `ruff.toml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "tk_comfyui_batch_image"
version = "0.1.0"
description = "ComfyUI custom node set for batch comic-page generation from a JSON script"
requires-python = ">=3.10"
dependencies = [
    "Pillow>=10.0",
    "jsonschema>=4.0",
    "numpy>=1.23",
]

[project.optional-dependencies]
dev = [
    "pytest>=7",
    "pytest-cov>=4",
    "ruff>=0.3",
]

[tool.setuptools.packages.find]
include = ["tk_comfyui_batch_image*"]
```

- [ ] **Step 2: Create `tk_comfyui_batch_image/__init__.py` (entry point)**

```python
"""ComfyUI custom nodes for batch comic generation."""
from .nodes.script_loader import ComicScriptLoader
from .nodes.batch_generator import ComicBatchGenerator
from .nodes.page_composer import ComicPageComposer

NODE_CLASS_MAPPINGS = {
    "ComicScriptLoader": ComicScriptLoader,
    "ComicBatchGenerator": ComicBatchGenerator,
    "ComicPageComposer": ComicPageComposer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComicScriptLoader": "Comic Script Loader",
    "ComicBatchGenerator": "Comic Batch Generator",
    "ComicPageComposer": "Comic Page Composer",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

Note: this file will fail to import until Task 10–12 create the three node classes. That's expected — later tasks will unblock it.

- [ ] **Step 3: Create empty package `__init__.py` for sub-packages**

```python
# tk_comfyui_batch_image/nodes/__init__.py
# tk_comfyui_batch_image/core/__init__.py
# tk_comfyui_batch_image/tests/__init__.py
```

All three files contain a single blank line.

- [ ] **Step 4: Create `ruff.toml`**

```toml
line-length = 100
target-version = "py310"

[lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM"]
ignore = ["E501"]  # long strings in prompts are ok
```

- [ ] **Step 5: Create `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
.superpowers/
.omc/
output/
```

- [ ] **Step 6: Create minimal `README.md`**

```markdown
# tk_comfyui_batch_image

ComfyUI custom nodes for batch comic-page generation from a JSON script.

**Status:** M1 — Rectangle vertical-stack only. See `docs/superpowers/` for spec & plans.
```

- [ ] **Step 7: Verify `pip install -e .[dev]` runs**

Run: `pip install -e .[dev]`
Expected: successful install (may fail to load the package entry because nodes don't exist yet — that's fine; only the build metadata matters here).

---

## Task 2: `core/types.py` — ComfyUI custom type & core dataclasses

**Files:**
- Create: `tk_comfyui_batch_image/core/types.py`
- Create: `tk_comfyui_batch_image/core/constants.py`
- Create: `tk_comfyui_batch_image/tests/test_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_types.py
from tk_comfyui_batch_image.core.types import (
    COMIC_SCRIPT_TYPE, SolvedPanel, SolvedPage, SolvedScript
)


def test_comic_script_type_name():
    assert COMIC_SCRIPT_TYPE == "COMIC_SCRIPT"


def test_solved_panel_has_required_fields():
    p = SolvedPanel(
        page_index=1, panel_index=1, global_index=0,
        positive_prompt="a", negative_prompt="b",
        width_px=100, height_px=80,
        bbox_topleft=(10, 10), bbox_size=(100, 80),
        align="center",
        shape_type="rect",
        polygon_local=None, polygon_abs=None,
        seed=42,
        sampler={"sampler_name": "euler", "scheduler": "normal",
                 "steps": 25, "cfg": 7.0, "denoise": 1.0},
        border={"width_px": 3, "color": "#000000", "style": "solid"},
    )
    assert p.page_index == 1
    assert p.bbox_size == (100, 80)


def test_solved_page_aggregates_panels():
    sp = SolvedPage(page_index=1, page_width=500, page_height=700,
                    bleed_px=10, background="#FFFFFF", panels=[])
    assert sp.page_index == 1
    assert sp.panels == []


def test_solved_script_carries_book_level():
    script = SolvedScript(
        version="1.0", job_id="test", reading_direction="ltr",
        base_seed=12345, pages=[],
    )
    assert script.job_id == "test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `core/constants.py`**

```python
"""Shared constants: page templates, enums."""

PAGE_TEMPLATES: dict[str, tuple[int, int]] = {
    "A4":            (2480, 3508),
    "B5":            (2079, 2953),
    "JP_Tankobon":   (2362, 3425),
    "Webtoon":       (1600, 12800),
}

READING_DIRECTIONS = ("ltr", "rtl")
SHAPE_TYPES = ("rect",)  # M1 only; M3 adds "split", M4 adds "polygon"
LAYOUT_MODES = ("vertical_stack",)  # M1 only
PANEL_ALIGNS = ("left", "center", "right")
ON_FAILURE_MODES = ("halt", "retry_then_skip")

DEFAULT_RETRIES = 2
```

- [ ] **Step 4: Write `core/types.py`**

```python
"""Runtime dataclasses for the solved (normalized) comic script."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

COMIC_SCRIPT_TYPE = "COMIC_SCRIPT"


@dataclass
class SolvedPanel:
    page_index: int
    panel_index: int
    global_index: int                # 0-based across whole book (for seed offset)
    positive_prompt: str
    negative_prompt: str
    width_px: int
    height_px: int
    bbox_topleft: tuple[int, int]    # absolute (x, y) on page canvas
    bbox_size: tuple[int, int]       # (w, h) — for rect = width_px × height_px
    align: str                        # "left" | "center" | "right"
    shape_type: str                   # "rect" in M1
    polygon_local: Optional[list[tuple[float, float]]]   # None for rect
    polygon_abs: Optional[list[tuple[int, int]]]         # None for rect
    seed: int
    sampler: dict                     # merged sampler settings
    border: dict                      # {"width_px": int, "color": "#RRGGBB", "style": str}


@dataclass
class SolvedPage:
    page_index: int
    page_width: int
    page_height: int
    bleed_px: int
    background: str                   # "#RRGGBB"
    panels: list[SolvedPanel] = field(default_factory=list)


@dataclass
class SolvedScript:
    version: str
    job_id: str
    reading_direction: str
    base_seed: int
    pages: list[SolvedPage] = field(default_factory=list)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tk_comfyui_batch_image/tests/test_types.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git init  # if not yet a repo
git add pyproject.toml README.md ruff.toml .gitignore \
  tk_comfyui_batch_image/__init__.py \
  tk_comfyui_batch_image/nodes/__init__.py \
  tk_comfyui_batch_image/core/__init__.py \
  tk_comfyui_batch_image/core/types.py \
  tk_comfyui_batch_image/core/constants.py \
  tk_comfyui_batch_image/tests/__init__.py \
  tk_comfyui_batch_image/tests/test_types.py
git commit -m "feat(core): scaffold package + SolvedScript/Page/Panel types"
```

---

## Task 3: `core/schema.py` — M1 JSON Schema

**Files:**
- Create: `tk_comfyui_batch_image/core/schema.py`
- Create: `tk_comfyui_batch_image/tests/test_schema.py`
- Create: `tk_comfyui_batch_image/tests/fixtures/scripts/minimal.json`
- Create: `tk_comfyui_batch_image/tests/fixtures/scripts/basic.json`

- [ ] **Step 1: Write fixtures**

`tests/fixtures/scripts/minimal.json`:
```json
{
  "version": "1.0",
  "job_id": "min",
  "reading_direction": "ltr",
  "page_template": "custom",
  "page_width_px": 512,
  "page_height_px": 768,
  "bleed_px": 20,
  "gutter_px": 10,
  "page_background": "#FFFFFF",
  "base_seed": 7,
  "style_prompt":     { "positive": "anime style", "negative": "blurry" },
  "character_prompt": { "positive": "a girl, short hair", "negative": "" },
  "default_sampler":  { "sampler_name": "euler", "scheduler": "normal", "steps": 20, "cfg": 7.0, "denoise": 1.0 },
  "default_border":   { "width_px": 2, "color": "#000000", "style": "solid" },
  "pages": [
    {
      "page_index": 1,
      "page_prompt": { "positive": "", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        {
          "panel_index": 1,
          "scene_prompt": { "positive": "looking at sky", "negative": "" },
          "width_px": 472,
          "height_px": 300,
          "align": "center",
          "shape": { "type": "rect" }
        }
      ]
    }
  ]
}
```

`tests/fixtures/scripts/basic.json`:
```json
{
  "version": "1.0",
  "job_id": "basic",
  "reading_direction": "ltr",
  "page_template": "custom",
  "page_width_px": 512,
  "page_height_px": 768,
  "bleed_px": 20,
  "gutter_px": 10,
  "page_background": "#FFFFFF",
  "base_seed": 7,
  "style_prompt":     { "positive": "anime style", "negative": "blurry" },
  "character_prompt": { "positive": "a girl", "negative": "" },
  "default_sampler":  { "sampler_name": "euler", "scheduler": "normal", "steps": 20, "cfg": 7.0, "denoise": 1.0 },
  "default_border":   { "width_px": 2, "color": "#000000", "style": "solid" },
  "pages": [
    {
      "page_index": 1,
      "page_prompt": { "positive": "", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        { "panel_index": 1, "scene_prompt": { "positive": "scene A", "negative": "" },
          "width_px": 472, "height_px": 200, "align": "center", "shape": { "type": "rect" } },
        { "panel_index": 2, "scene_prompt": { "positive": "scene B", "negative": "" },
          "width_px": 472, "height_px": 200, "align": "left",   "shape": { "type": "rect" } },
        { "panel_index": 3, "scene_prompt": { "positive": "scene C", "negative": "" },
          "width_px": 472, "height_px": 200, "align": "right",  "shape": { "type": "rect" } }
      ]
    },
    {
      "page_index": 2,
      "page_prompt": { "positive": "night", "negative": "" },
      "layout_mode": "vertical_stack",
      "panels": [
        { "panel_index": 1, "scene_prompt": { "positive": "scene D", "negative": "" },
          "width_px": 472, "height_px": 400, "align": "center", "shape": { "type": "rect" },
          "sampler_override": { "steps": 30, "cfg": 8.0 } }
      ]
    }
  ]
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_schema.py
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from tk_comfyui_batch_image.core.schema import COMIC_SCHEMA

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(COMIC_SCHEMA)


def test_minimal_fixture_validates():
    data = json.loads((FIXTURES / "minimal.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(COMIC_SCHEMA).iter_errors(data))
    assert errors == [], errors


def test_basic_fixture_validates():
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(COMIC_SCHEMA).iter_errors(data))
    assert errors == [], errors


def test_missing_version_is_rejected():
    data = json.loads((FIXTURES / "minimal.json").read_text(encoding="utf-8"))
    del data["version"]
    errors = list(Draft202012Validator(COMIC_SCHEMA).iter_errors(data))
    assert any("version" in e.message or "'version' is a required property" in e.message for e in errors)


def test_unknown_shape_type_is_rejected():
    data = json.loads((FIXTURES / "minimal.json").read_text(encoding="utf-8"))
    data["pages"][0]["panels"][0]["shape"]["type"] = "hexagon"
    errors = list(Draft202012Validator(COMIC_SCHEMA).iter_errors(data))
    assert errors, "expected schema to reject shape.type=hexagon"


def test_negative_angle_out_of_range_is_rejected():
    # M1 only has "rect" so nothing with angle yet — skip pattern established for later
    pass


def test_unknown_top_level_property_is_rejected():
    data = json.loads((FIXTURES / "minimal.json").read_text(encoding="utf-8"))
    data["rogue_field"] = "nope"
    errors = list(Draft202012Validator(COMIC_SCHEMA).iter_errors(data))
    assert errors
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...schema'`.

- [ ] **Step 4: Write `core/schema.py`**

```python
"""M1 JSON Schema for comic script. Rect-only; shape_group and polygon are M3/M4."""
from __future__ import annotations

_HEX_COLOR = {"type": "string", "pattern": r"^#[0-9A-Fa-f]{6}$"}

_PROMPT_PAIR = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "positive": {"type": "string"},
        "negative": {"type": "string"},
    },
    "required": ["positive", "negative"],
}

_SAMPLER = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "sampler_name": {"type": "string", "minLength": 1},
        "scheduler":    {"type": "string", "minLength": 1},
        "steps":        {"type": "integer", "minimum": 1, "maximum": 200},
        "cfg":          {"type": "number",  "minimum": 0.0, "maximum": 30.0},
        "denoise":      {"type": "number",  "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["sampler_name", "scheduler", "steps", "cfg", "denoise"],
}

_SAMPLER_OVERRIDE = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "seed":         {"type": "integer", "minimum": 0},
        "sampler_name": {"type": "string", "minLength": 1},
        "scheduler":    {"type": "string", "minLength": 1},
        "steps":        {"type": "integer", "minimum": 1, "maximum": 200},
        "cfg":          {"type": "number",  "minimum": 0.0, "maximum": 30.0},
        "denoise":      {"type": "number",  "minimum": 0.0, "maximum": 1.0},
    },
}

_BORDER = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "width_px": {"type": "integer", "minimum": 0, "maximum": 50},
        "color":    _HEX_COLOR,
        "style":    {"enum": ["solid"]},
    },
    "required": ["width_px", "color", "style"],
}

_SHAPE = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "type": {"enum": ["rect"]},   # M3/M4 add "split", "polygon"
    },
    "required": ["type"],
}

_PANEL = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "panel_index": {"type": "integer", "minimum": 1},
        "scene_prompt": _PROMPT_PAIR,
        "width_px":  {"type": "integer", "minimum": 32, "maximum": 16384},
        "height_px": {"type": "integer", "minimum": 32, "maximum": 16384},
        "align": {"enum": ["left", "center", "right"]},
        "shape": _SHAPE,
        "border": _BORDER,
        "sampler_override": _SAMPLER_OVERRIDE,
    },
    "required": ["panel_index", "scene_prompt", "width_px", "height_px", "align", "shape"],
}

_PAGE = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "page_index":  {"type": "integer", "minimum": 1},
        "page_prompt": _PROMPT_PAIR,
        "layout_mode": {"enum": ["vertical_stack"]},
        "gutter_px":   {"type": "integer", "minimum": 0, "maximum": 500},
        "panels":      {"type": "array", "minItems": 1, "items": _PANEL},
    },
    "required": ["page_index", "page_prompt", "layout_mode", "panels"],
}

COMIC_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://tk/comfyui/comic-schema/1.0",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "version":            {"enum": ["1.0"]},
        "job_id":             {"type": "string", "pattern": r"^[A-Za-z0-9_\-]{1,64}$"},
        "reading_direction":  {"enum": ["ltr", "rtl"]},
        "page_template":      {"enum": ["A4", "B5", "JP_Tankobon", "Webtoon", "custom"]},
        "page_width_px":      {"type": "integer", "minimum": 64, "maximum": 16384},
        "page_height_px":     {"type": "integer", "minimum": 64, "maximum": 65535},
        "bleed_px":           {"type": "integer", "minimum": 0, "maximum": 1000},
        "gutter_px":          {"type": "integer", "minimum": 0, "maximum": 500},
        "page_background":    _HEX_COLOR,
        "base_seed":          {"type": "integer", "minimum": 0, "maximum": 2**63 - 1},
        "style_prompt":       _PROMPT_PAIR,
        "character_prompt":   _PROMPT_PAIR,
        "default_sampler":    _SAMPLER,
        "default_border":     _BORDER,
        "pages":              {"type": "array", "minItems": 1, "items": _PAGE},
    },
    "required": [
        "version", "job_id", "reading_direction", "page_template",
        "bleed_px", "gutter_px", "page_background", "base_seed",
        "style_prompt", "character_prompt",
        "default_sampler", "default_border", "pages",
    ],
}
```

- [ ] **Step 5: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_schema.py -v`
Expected: all 6 tests pass (the `test_negative_angle_out_of_range_is_rejected` is a no-op placeholder for M3).

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/core/schema.py \
        tk_comfyui_batch_image/tests/test_schema.py \
        tk_comfyui_batch_image/tests/fixtures/scripts/minimal.json \
        tk_comfyui_batch_image/tests/fixtures/scripts/basic.json
git commit -m "feat(core): add M1 JSON schema (rect-only) + fixtures"
```

---

## Task 4: `core/validator.py` — schema validation with readable errors

**Files:**
- Create: `tk_comfyui_batch_image/core/validator.py`
- Create: `tk_comfyui_batch_image/tests/test_validator.py`
- Create: `tk_comfyui_batch_image/tests/fixtures/scripts/invalid_missing_version.json`

- [ ] **Step 1: Write invalid fixture**

`tests/fixtures/scripts/invalid_missing_version.json`:
```json
{
  "job_id": "x",
  "reading_direction": "ltr",
  "page_template": "custom",
  "page_width_px": 512,
  "page_height_px": 768,
  "bleed_px": 20,
  "gutter_px": 10,
  "page_background": "#FFFFFF",
  "base_seed": 0,
  "style_prompt":     { "positive": "", "negative": "" },
  "character_prompt": { "positive": "", "negative": "" },
  "default_sampler":  { "sampler_name": "euler", "scheduler": "normal", "steps": 20, "cfg": 7.0, "denoise": 1.0 },
  "default_border":   { "width_px": 2, "color": "#000000", "style": "solid" },
  "pages": []
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_validator.py
import json
from pathlib import Path
import pytest
from tk_comfyui_batch_image.core.validator import validate_schema, ValidationError

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def test_valid_fixture_returns_none():
    data = json.loads((FIXTURES / "minimal.json").read_text(encoding="utf-8"))
    assert validate_schema(data) is None


def test_missing_version_raises_with_readable_message():
    data = json.loads((FIXTURES / "invalid_missing_version.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError) as exc:
        validate_schema(data)
    msg = str(exc.value)
    assert "version" in msg
    assert "required property" in msg or "missing" in msg


def test_error_path_is_included():
    data = json.loads((FIXTURES / "minimal.json").read_text(encoding="utf-8"))
    data["pages"][0]["panels"][0]["width_px"] = -1
    with pytest.raises(ValidationError) as exc:
        validate_schema(data)
    msg = str(exc.value)
    assert "pages[0].panels[0].width_px" in msg


def test_multiple_errors_all_reported():
    data = json.loads((FIXTURES / "minimal.json").read_text(encoding="utf-8"))
    data["page_background"] = "not-a-hex"
    data["pages"][0]["panels"][0]["align"] = "diagonal"
    with pytest.raises(ValidationError) as exc:
        validate_schema(data)
    msg = str(exc.value)
    assert "page_background" in msg
    assert "align" in msg
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_validator.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Write `core/validator.py`**

```python
"""Schema validation with human-readable error messages."""
from __future__ import annotations
from typing import Iterable
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
```

- [ ] **Step 5: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_validator.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/core/validator.py \
        tk_comfyui_batch_image/tests/test_validator.py \
        tk_comfyui_batch_image/tests/fixtures/scripts/invalid_missing_version.json
git commit -m "feat(core): add schema validator with path-aware errors"
```

---

## Task 5: `core/prompt_builder.py` — 4-layer prompt join

**Files:**
- Create: `tk_comfyui_batch_image/core/prompt_builder.py`
- Create: `tk_comfyui_batch_image/tests/test_prompt_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompt_builder.py
from tk_comfyui_batch_image.core.prompt_builder import build_prompt_pair


def test_all_layers_concatenated_with_commas():
    pos, neg = build_prompt_pair(
        style={"positive": "anime style", "negative": "blurry"},
        character={"positive": "a girl", "negative": "extra limbs"},
        page={"positive": "night", "negative": "daylight"},
        scene={"positive": "looking at sky", "negative": "crowd"},
        positive_suffix="masterpiece",
        negative_suffix="lowres",
    )
    assert pos == "anime style, a girl, night, looking at sky, masterpiece"
    assert neg == "blurry, extra limbs, daylight, crowd, lowres"


def test_empty_layers_are_skipped():
    pos, neg = build_prompt_pair(
        style={"positive": "", "negative": ""},
        character={"positive": "a girl", "negative": ""},
        page={"positive": "", "negative": ""},
        scene={"positive": "smile", "negative": ""},
        positive_suffix="",
        negative_suffix="",
    )
    assert pos == "a girl, smile"
    assert neg == ""


def test_whitespace_only_layers_are_skipped():
    pos, neg = build_prompt_pair(
        style={"positive": "   ", "negative": "  "},
        character={"positive": "hero", "negative": ""},
        page={"positive": "", "negative": ""},
        scene={"positive": "scene", "negative": ""},
        positive_suffix="",
        negative_suffix="",
    )
    assert pos == "hero, scene"
    assert neg == ""


def test_trailing_commas_in_layers_are_handled():
    pos, neg = build_prompt_pair(
        style={"positive": "anime,", "negative": ""},
        character={"positive": "girl, ", "negative": ""},
        page={"positive": "", "negative": ""},
        scene={"positive": "smile", "negative": ""},
        positive_suffix="",
        negative_suffix="",
    )
    assert pos == "anime, girl, smile"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_prompt_builder.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `core/prompt_builder.py`**

```python
"""4-layer prompt joiner: style + character + page + scene (+ suffix)."""
from __future__ import annotations


def _clean(s: str) -> str:
    # strip whitespace + trailing commas that users/LLMs sometimes add
    return s.strip().rstrip(",").strip()


def _join(parts: list[str]) -> str:
    return ", ".join(p for p in (_clean(x) for x in parts) if p)


def build_prompt_pair(
    *,
    style: dict,
    character: dict,
    page: dict,
    scene: dict,
    positive_suffix: str = "",
    negative_suffix: str = "",
) -> tuple[str, str]:
    """Return (positive, negative) concatenated prompts.

    Each layer dict has "positive" and "negative" keys. Empty / whitespace-only
    layers are skipped. Parts are joined with ", ".
    """
    pos = _join([style["positive"], character["positive"], page["positive"],
                 scene["positive"], positive_suffix])
    neg = _join([style["negative"], character["negative"], page["negative"],
                 scene["negative"], negative_suffix])
    return pos, neg
```

- [ ] **Step 4: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_prompt_builder.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/prompt_builder.py \
        tk_comfyui_batch_image/tests/test_prompt_builder.py
git commit -m "feat(core): add 4-layer prompt builder"
```

---

## Task 6: `core/layout_solver.py` — vertical_stack rect solver

**Files:**
- Create: `tk_comfyui_batch_image/core/layout_solver.py`
- Create: `tk_comfyui_batch_image/tests/test_layout_solver.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_layout_solver.py
import pytest
from tk_comfyui_batch_image.core.layout_solver import (
    solve_vertical_stack, LayoutError
)


def test_single_panel_centered():
    result = solve_vertical_stack(
        page_width=500, page_height=800, bleed_px=20, gutter_px=10,
        panels=[{"width_px": 400, "height_px": 300, "align": "center"}],
    )
    assert len(result) == 1
    assert result[0] == {"bbox_topleft": (50, 20), "bbox_size": (400, 300)}


def test_three_panels_stacked_with_gutter():
    result = solve_vertical_stack(
        page_width=500, page_height=800, bleed_px=20, gutter_px=10,
        panels=[
            {"width_px": 460, "height_px": 200, "align": "center"},
            {"width_px": 460, "height_px": 200, "align": "left"},
            {"width_px": 460, "height_px": 200, "align": "right"},
        ],
    )
    assert result[0]["bbox_topleft"] == (20, 20)
    assert result[1]["bbox_topleft"] == (20, 230)   # 20 + 200 + 10
    assert result[2]["bbox_topleft"] == (20, 440)
    assert all(r["bbox_size"] == (460, 200) for r in result)


def test_align_left_positions_at_bleed():
    result = solve_vertical_stack(
        page_width=500, page_height=800, bleed_px=20, gutter_px=0,
        panels=[{"width_px": 200, "height_px": 100, "align": "left"}],
    )
    assert result[0]["bbox_topleft"] == (20, 20)


def test_align_right_positions_against_right_bleed():
    result = solve_vertical_stack(
        page_width=500, page_height=800, bleed_px=20, gutter_px=0,
        panels=[{"width_px": 200, "height_px": 100, "align": "right"}],
    )
    # right edge = 500 - 20 = 480; x = 480 - 200 = 280
    assert result[0]["bbox_topleft"] == (280, 20)


def test_overflow_raises():
    with pytest.raises(LayoutError) as exc:
        solve_vertical_stack(
            page_width=500, page_height=400, bleed_px=20, gutter_px=10,
            panels=[
                {"width_px": 460, "height_px": 300, "align": "center"},
                {"width_px": 460, "height_px": 300, "align": "center"},
            ],
        )
    assert "exceeds inner content area" in str(exc.value)


def test_panel_wider_than_inner_area_raises():
    with pytest.raises(LayoutError) as exc:
        solve_vertical_stack(
            page_width=500, page_height=800, bleed_px=20, gutter_px=0,
            panels=[{"width_px": 600, "height_px": 100, "align": "center"}],
        )
    assert "panel 0 width" in str(exc.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_layout_solver.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `core/layout_solver.py`**

```python
"""Resolve panel absolute bboxes for supported layout modes.

M1 supports `vertical_stack` with rect panels only.
"""
from __future__ import annotations


class LayoutError(ValueError):
    """Raised when layout cannot be resolved."""


def solve_vertical_stack(
    *,
    page_width: int,
    page_height: int,
    bleed_px: int,
    gutter_px: int,
    panels: list[dict],
) -> list[dict]:
    """Return one dict per panel: {bbox_topleft: (x,y), bbox_size: (w,h)}.

    Panels are stacked top-to-bottom with `gutter_px` between them.
    Horizontal alignment respects `align` in {"left","center","right"} relative
    to the inner content area (page minus bleed on each side).
    """
    inner_left   = bleed_px
    inner_right  = page_width - bleed_px
    inner_top    = bleed_px
    inner_bottom = page_height - bleed_px
    inner_w = inner_right - inner_left
    inner_h = inner_bottom - inner_top
    if inner_w <= 0 or inner_h <= 0:
        raise LayoutError(f"bleed_px {bleed_px} too large for page {page_width}x{page_height}")

    total_h = sum(p["height_px"] for p in panels) + gutter_px * max(0, len(panels) - 1)
    if total_h > inner_h:
        raise LayoutError(
            f"vertical_stack: total panel height {sum(p['height_px'] for p in panels)}px + "
            f"gutters {gutter_px * max(0, len(panels)-1)}px = {total_h}px "
            f"exceeds inner content area {inner_h}px (page {page_height} - bleed*2). "
            f"hint: reduce a panel height or increase page_height_px."
        )

    results: list[dict] = []
    y = inner_top
    for i, p in enumerate(panels):
        w, h, align = p["width_px"], p["height_px"], p["align"]
        if w > inner_w:
            raise LayoutError(
                f"panel {i} width {w}px exceeds inner content width {inner_w}px"
            )
        if align == "left":
            x = inner_left
        elif align == "right":
            x = inner_right - w
        else:  # center
            x = inner_left + (inner_w - w) // 2
        results.append({"bbox_topleft": (x, y), "bbox_size": (w, h)})
        y += h + gutter_px
    return results
```

- [ ] **Step 4: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_layout_solver.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/layout_solver.py \
        tk_comfyui_batch_image/tests/test_layout_solver.py
git commit -m "feat(core): add vertical_stack rect layout solver"
```

---

## Task 7: `core/normalizer.py` — merge defaults, compute panels_solved

**Files:**
- Create: `tk_comfyui_batch_image/core/normalizer.py`
- Create: `tk_comfyui_batch_image/tests/test_normalizer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_normalizer.py
import json
from pathlib import Path
from tk_comfyui_batch_image.core.normalizer import normalize_script
from tk_comfyui_batch_image.core.types import SolvedScript, SolvedPage, SolvedPanel

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_normalize_minimal_returns_solved_script():
    s = normalize_script(_load("minimal.json"))
    assert isinstance(s, SolvedScript)
    assert s.job_id == "min"
    assert len(s.pages) == 1
    assert len(s.pages[0].panels) == 1

    p = s.pages[0].panels[0]
    assert isinstance(p, SolvedPanel)
    assert p.page_index == 1
    assert p.panel_index == 1
    assert p.global_index == 0
    assert p.width_px == 472
    assert p.bbox_size == (472, 300)
    assert p.shape_type == "rect"
    assert p.polygon_local is None


def test_prompt_is_concatenated():
    s = normalize_script(_load("minimal.json"))
    p = s.pages[0].panels[0]
    assert p.positive_prompt == "anime style, a girl, short hair, looking at sky"
    assert p.negative_prompt == "blurry"


def test_sampler_override_merges_over_defaults():
    s = normalize_script(_load("basic.json"))
    p21 = s.pages[1].panels[0]
    assert p21.sampler["steps"] == 30    # overridden
    assert p21.sampler["cfg"] == 8.0     # overridden
    assert p21.sampler["sampler_name"] == "euler"  # inherited


def test_seed_offset_uses_global_index():
    s = normalize_script(_load("basic.json"))
    seeds = [panel.seed for page in s.pages for panel in page.panels]
    assert seeds == [7, 8, 9, 10]  # base_seed=7, 3 panels in p1 + 1 in p2


def test_page_template_custom_uses_explicit_size():
    s = normalize_script(_load("minimal.json"))
    assert s.pages[0].page_width == 512
    assert s.pages[0].page_height == 768


def test_page_template_A4_overrides_explicit_size():
    data = _load("minimal.json")
    data["page_template"] = "A4"
    data["page_width_px"] = 100    # should be ignored
    data["page_height_px"] = 100
    # Need a panel that fits A4
    data["pages"][0]["panels"][0]["width_px"] = 2000
    s = normalize_script(data)
    assert s.pages[0].page_width == 2480
    assert s.pages[0].page_height == 3508


def test_border_inherits_then_overrides():
    data = _load("minimal.json")
    data["pages"][0]["panels"][0]["border"] = {"width_px": 5, "color": "#FF0000", "style": "solid"}
    s = normalize_script(data)
    assert s.pages[0].panels[0].border == {"width_px": 5, "color": "#FF0000", "style": "solid"}


def test_panels_solved_includes_bbox_from_layout():
    s = normalize_script(_load("basic.json"))
    p1 = s.pages[0].panels[0]
    # inner area 20~492 × 20~748; panel w=472, align=center → x = 20
    assert p1.bbox_topleft == (20, 20)
    assert p1.bbox_size == (472, 200)
    # second panel
    p2 = s.pages[0].panels[1]
    assert p2.bbox_topleft == (20, 230)  # 20 + 200 + 10 gutter
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_normalizer.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `core/normalizer.py`**

```python
"""Normalize a validated JSON dict into a SolvedScript with fully-resolved panels."""
from __future__ import annotations
from .constants import PAGE_TEMPLATES
from .layout_solver import solve_vertical_stack
from .prompt_builder import build_prompt_pair
from .types import SolvedPage, SolvedPanel, SolvedScript


def _resolve_page_size(data: dict) -> tuple[int, int]:
    tpl = data["page_template"]
    if tpl == "custom":
        return int(data["page_width_px"]), int(data["page_height_px"])
    if tpl in PAGE_TEMPLATES:
        return PAGE_TEMPLATES[tpl]
    raise ValueError(f"unknown page_template: {tpl}")


def normalize_script(data: dict) -> SolvedScript:
    """Validated JSON dict → SolvedScript with resolved bboxes, prompts, sampler, seeds."""
    page_w, page_h = _resolve_page_size(data)
    bleed   = int(data["bleed_px"])
    gutter  = int(data["gutter_px"])
    bg      = data["page_background"]
    base_seed = int(data["base_seed"])
    default_sampler = dict(data["default_sampler"])
    default_border  = dict(data["default_border"])

    style_p = data["style_prompt"]
    char_p  = data["character_prompt"]

    pages: list[SolvedPage] = []
    global_idx = 0
    for page in data["pages"]:
        page_prompt = page["page_prompt"]
        page_gutter = int(page.get("gutter_px", gutter))
        page_panels_raw = page["panels"]

        # solve layout for rect panels
        bbox_specs = solve_vertical_stack(
            page_width=page_w, page_height=page_h,
            bleed_px=bleed, gutter_px=page_gutter,
            panels=[{"width_px": p["width_px"], "height_px": p["height_px"],
                     "align": p["align"]} for p in page_panels_raw],
        )

        solved_panels: list[SolvedPanel] = []
        for raw, bb in zip(page_panels_raw, bbox_specs):
            pos, neg = build_prompt_pair(
                style=style_p, character=char_p,
                page=page_prompt, scene=raw["scene_prompt"],
            )
            override = raw.get("sampler_override") or {}
            merged_sampler = {**default_sampler, **{k: v for k, v in override.items() if k != "seed"}}
            seed = int(override["seed"]) if "seed" in override else base_seed + global_idx
            border = dict(raw.get("border") or default_border)

            solved_panels.append(SolvedPanel(
                page_index=int(page["page_index"]),
                panel_index=int(raw["panel_index"]),
                global_index=global_idx,
                positive_prompt=pos,
                negative_prompt=neg,
                width_px=int(raw["width_px"]),
                height_px=int(raw["height_px"]),
                bbox_topleft=bb["bbox_topleft"],
                bbox_size=bb["bbox_size"],
                align=raw["align"],
                shape_type=raw["shape"]["type"],
                polygon_local=None,
                polygon_abs=None,
                seed=seed,
                sampler=merged_sampler,
                border=border,
            ))
            global_idx += 1

        pages.append(SolvedPage(
            page_index=int(page["page_index"]),
            page_width=page_w, page_height=page_h,
            bleed_px=bleed, background=bg,
            panels=solved_panels,
        ))

    return SolvedScript(
        version=data["version"],
        job_id=data["job_id"],
        reading_direction=data["reading_direction"],
        base_seed=base_seed,
        pages=pages,
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_normalizer.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/normalizer.py \
        tk_comfyui_batch_image/tests/test_normalizer.py
git commit -m "feat(core): add script normalizer (defaults + layout + prompts + seeds)"
```

---

## Task 8: `core/cache_manager.py` — panel hash & resume

**Files:**
- Create: `tk_comfyui_batch_image/core/cache_manager.py`
- Create: `tk_comfyui_batch_image/tests/test_cache_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cache_manager.py
from pathlib import Path
from tk_comfyui_batch_image.core.cache_manager import (
    panel_hash, panel_paths, read_manifest, write_manifest, manifest_matches
)
from tk_comfyui_batch_image.core.types import SolvedPanel


def _panel(**overrides) -> SolvedPanel:
    base = dict(
        page_index=1, panel_index=1, global_index=0,
        positive_prompt="a", negative_prompt="b",
        width_px=100, height_px=80,
        bbox_topleft=(10, 10), bbox_size=(100, 80),
        align="center", shape_type="rect",
        polygon_local=None, polygon_abs=None,
        seed=42,
        sampler={"sampler_name": "euler", "scheduler": "normal",
                 "steps": 25, "cfg": 7.0, "denoise": 1.0},
        border={"width_px": 3, "color": "#000000", "style": "solid"},
    )
    base.update(overrides)
    return SolvedPanel(**base)


def test_hash_is_deterministic():
    a = panel_hash(_panel())
    b = panel_hash(_panel())
    assert a == b
    assert len(a) == 64   # sha256 hex


def test_hash_changes_when_prompt_changes():
    a = panel_hash(_panel(positive_prompt="a"))
    b = panel_hash(_panel(positive_prompt="b"))
    assert a != b


def test_hash_changes_when_seed_changes():
    assert panel_hash(_panel(seed=1)) != panel_hash(_panel(seed=2))


def test_hash_changes_when_sampler_changes():
    s2 = {"sampler_name": "euler", "scheduler": "normal",
          "steps": 99, "cfg": 7.0, "denoise": 1.0}
    assert panel_hash(_panel()) != panel_hash(_panel(sampler=s2))


def test_hash_independent_of_bbox_topleft():
    # bbox position changes when gutter changes, but image content doesn't depend on it
    assert panel_hash(_panel(bbox_topleft=(0, 0))) == panel_hash(_panel(bbox_topleft=(50, 50)))


def test_panel_paths(tmp_path: Path):
    paths = panel_paths(tmp_path, _panel(page_index=3, panel_index=12))
    assert paths.image.name == "p003_12.png"
    assert paths.manifest.name == "p003_12.json"
    assert paths.image.parent == tmp_path / "panels"


def test_write_then_read_manifest_roundtrip(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    paths.image.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, panel_hash(p), extra={"elapsed_s": 3.2})
    m = read_manifest(paths.manifest)
    assert m["hash"] == panel_hash(p)
    assert m["elapsed_s"] == 3.2


def test_manifest_matches_true(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    paths.image.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, panel_hash(p))
    assert manifest_matches(paths.manifest, p) is True


def test_manifest_matches_false_when_prompt_changed(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    paths.image.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, panel_hash(p))
    p2 = _panel(positive_prompt="different")
    assert manifest_matches(paths.manifest, p2) is False


def test_manifest_matches_false_when_no_file(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    assert manifest_matches(paths.manifest, p) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_cache_manager.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `core/cache_manager.py`**

```python
"""Panel-hash-based cache: compute stable hash, read/write manifest, detect stale."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from .types import SolvedPanel


@dataclass(frozen=True)
class PanelPaths:
    image: Path
    manifest: Path


def panel_hash(panel: SolvedPanel) -> str:
    """Stable SHA256 over the fields that determine the generated image.

    Deliberately excludes bbox_topleft (affects composition, not pixels).
    """
    payload = {
        "positive_prompt": panel.positive_prompt,
        "negative_prompt": panel.negative_prompt,
        "width_px":  panel.width_px,
        "height_px": panel.height_px,
        "seed": panel.seed,
        "sampler": dict(sorted(panel.sampler.items())),
        "shape_type": panel.shape_type,
        "polygon_local": panel.polygon_local,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def panel_paths(out_dir: Path, panel: SolvedPanel) -> PanelPaths:
    panels_dir = Path(out_dir) / "panels"
    stem = f"p{panel.page_index:03d}_{panel.panel_index:02d}"
    return PanelPaths(
        image=panels_dir / f"{stem}.png",
        manifest=panels_dir / f"{stem}.json",
    )


def write_manifest(path: Path, hash_hex: str, extra: Optional[dict] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"hash": hash_hex}
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_matches(manifest_path: Path, panel: SolvedPanel) -> bool:
    if not manifest_path.exists():
        return False
    try:
        m = read_manifest(manifest_path)
    except (OSError, json.JSONDecodeError):
        return False
    return m.get("hash") == panel_hash(panel)
```

- [ ] **Step 4: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_cache_manager.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/cache_manager.py \
        tk_comfyui_batch_image/tests/test_cache_manager.py
git commit -m "feat(core): add panel-hash cache manager for resume"
```

---

## Task 9: `core/sampler_runner.py` — ComfyUI-free sampler abstraction

This module wraps the ComfyUI `KSampler` / `CLIPTextEncode` / `VAEDecode` calls behind a thin protocol so tests can inject a fake. The node layer (Task 11) supplies the real ComfyUI callables.

**Files:**
- Create: `tk_comfyui_batch_image/core/sampler_runner.py`
- Create: `tk_comfyui_batch_image/tests/test_sampler_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sampler_runner.py
import numpy as np
from tk_comfyui_batch_image.core.sampler_runner import (
    SamplerBackend, run_panel_sampler
)
from tk_comfyui_batch_image.core.types import SolvedPanel


class FakeBackend(SamplerBackend):
    """Deterministic backend: returns a solid grey image of requested size."""

    def __init__(self):
        self.calls = []

    def encode(self, clip, text):
        self.calls.append(("encode", text))
        return ("COND", text)

    def empty_latent(self, width, height, batch_size=1):
        self.calls.append(("latent", width, height))
        return {"w": width, "h": height, "bs": batch_size}

    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               cond_pos, cond_neg, latent, denoise):
        self.calls.append(("sample", seed, steps, cfg))
        return latent

    def vae_decode(self, vae, samples):
        self.calls.append(("decode",))
        # return (H, W, 3) float32 0~1 grey image
        h, w = samples["h"], samples["w"]
        img = np.full((h, w, 3), 0.5, dtype=np.float32)
        return img


def _panel(**overrides) -> SolvedPanel:
    base = dict(
        page_index=1, panel_index=1, global_index=0,
        positive_prompt="pos", negative_prompt="neg",
        width_px=64, height_px=48,
        bbox_topleft=(0, 0), bbox_size=(64, 48),
        align="center", shape_type="rect",
        polygon_local=None, polygon_abs=None,
        seed=99,
        sampler={"sampler_name": "euler", "scheduler": "normal",
                 "steps": 10, "cfg": 7.0, "denoise": 1.0},
        border={"width_px": 0, "color": "#000000", "style": "solid"},
    )
    base.update(overrides)
    return SolvedPanel(**base)


def test_run_panel_sampler_calls_backend_in_order():
    b = FakeBackend()
    img = run_panel_sampler(b, model="M", clip="C", vae="V", panel=_panel())
    kinds = [c[0] for c in b.calls]
    assert kinds == ["encode", "encode", "latent", "sample", "decode"]
    assert img.shape == (48, 64, 3)
    assert img.dtype == np.float32


def test_run_panel_sampler_passes_seed_and_steps():
    b = FakeBackend()
    run_panel_sampler(b, model="M", clip="C", vae="V",
                      panel=_panel(seed=12345,
                                   sampler={"sampler_name": "dpmpp_2m", "scheduler": "karras",
                                            "steps": 30, "cfg": 8.5, "denoise": 1.0}))
    sample_call = next(c for c in b.calls if c[0] == "sample")
    assert sample_call == ("sample", 12345, 30, 8.5)


def test_run_panel_sampler_requests_correct_latent_size():
    b = FakeBackend()
    run_panel_sampler(b, model="M", clip="C", vae="V",
                      panel=_panel(width_px=128, height_px=96, bbox_size=(128, 96)))
    latent_call = next(c for c in b.calls if c[0] == "latent")
    assert latent_call == ("latent", 128, 96)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_sampler_runner.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `core/sampler_runner.py`**

```python
"""Backend-agnostic sampler runner.

The real ComfyUI backend is wired up in `nodes/batch_generator.py`; tests inject
a fake backend for deterministic unit tests.
"""
from __future__ import annotations
from typing import Protocol
import numpy as np
from .types import SolvedPanel


class SamplerBackend(Protocol):
    def encode(self, clip, text: str): ...
    def empty_latent(self, width: int, height: int, batch_size: int = 1): ...
    def sample(self, model, seed: int, steps: int, cfg: float,
               sampler_name: str, scheduler: str,
               cond_pos, cond_neg, latent, denoise: float): ...
    def vae_decode(self, vae, samples) -> np.ndarray: ...


def run_panel_sampler(
    backend: SamplerBackend,
    *,
    model,
    clip,
    vae,
    panel: SolvedPanel,
) -> np.ndarray:
    """Run the full CLIP→KSampler→VAE decode pipeline for one panel.

    Returns an (H, W, 3) float32 image in [0, 1].
    """
    cond_pos = backend.encode(clip, panel.positive_prompt)
    cond_neg = backend.encode(clip, panel.negative_prompt)
    w, h = panel.bbox_size
    latent = backend.empty_latent(w, h, batch_size=1)
    s = panel.sampler
    samples = backend.sample(
        model, panel.seed, s["steps"], s["cfg"],
        s["sampler_name"], s["scheduler"],
        cond_pos, cond_neg, latent, s["denoise"],
    )
    img = backend.vae_decode(vae, samples)
    return img
```

- [ ] **Step 4: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_sampler_runner.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/sampler_runner.py \
        tk_comfyui_batch_image/tests/test_sampler_runner.py
git commit -m "feat(core): add backend-agnostic sampler runner"
```

---

## Task 10: `core/compositor.py` — paste rect panels + border

**Files:**
- Create: `tk_comfyui_batch_image/core/compositor.py`
- Create: `tk_comfyui_batch_image/tests/test_compositor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_compositor.py
import numpy as np
from PIL import Image
from tk_comfyui_batch_image.core.compositor import compose_page
from tk_comfyui_batch_image.core.types import SolvedPage, SolvedPanel


def _solid_img(w: int, h: int, rgb: tuple[int, int, int]) -> np.ndarray:
    arr = np.full((h, w, 3), 0, dtype=np.float32)
    arr[..., 0] = rgb[0] / 255.0
    arr[..., 1] = rgb[1] / 255.0
    arr[..., 2] = rgb[2] / 255.0
    return arr


def _panel(page_i, panel_i, topleft, size, border_w=0) -> SolvedPanel:
    return SolvedPanel(
        page_index=page_i, panel_index=panel_i, global_index=0,
        positive_prompt="", negative_prompt="",
        width_px=size[0], height_px=size[1],
        bbox_topleft=topleft, bbox_size=size,
        align="center", shape_type="rect",
        polygon_local=None, polygon_abs=None,
        seed=0,
        sampler={"sampler_name":"euler","scheduler":"normal","steps":1,"cfg":1.0,"denoise":1.0},
        border={"width_px": border_w, "color": "#000000", "style": "solid"},
    )


def test_compose_single_rect_panel_on_white_page():
    page = SolvedPage(page_index=1, page_width=200, page_height=300,
                      bleed_px=10, background="#FFFFFF", panels=[])
    p = _panel(1, 1, topleft=(10, 10), size=(180, 100))
    img = _solid_img(180, 100, (255, 0, 0))
    out = compose_page(page, [(p, img)])
    assert out.size == (200, 300)
    out_arr = np.array(out)
    # pixel inside panel is red
    assert tuple(out_arr[50, 100]) == (255, 0, 0)
    # pixel in bleed area is white
    assert tuple(out_arr[5, 5]) == (255, 255, 255)


def test_compose_draws_border():
    page = SolvedPage(page_index=1, page_width=200, page_height=200,
                      bleed_px=10, background="#FFFFFF", panels=[])
    p = _panel(1, 1, topleft=(20, 20), size=(100, 100), border_w=4)
    img = _solid_img(100, 100, (0, 255, 0))
    out = compose_page(page, [(p, img)])
    out_arr = np.array(out)
    # Top-left corner of border
    assert tuple(out_arr[20, 20]) == (0, 0, 0)
    # Inside panel (past border)
    assert tuple(out_arr[70, 70]) == (0, 255, 0)


def test_compose_multiple_panels_gutter_background():
    page = SolvedPage(page_index=1, page_width=200, page_height=400,
                      bleed_px=10, background="#808080", panels=[])
    p1 = _panel(1, 1, topleft=(10, 10), size=(180, 100))
    p2 = _panel(1, 2, topleft=(10, 130), size=(180, 100))  # 20-gap gutter
    img_r = _solid_img(180, 100, (255, 0, 0))
    img_g = _solid_img(180, 100, (0, 255, 0))
    out = compose_page(page, [(p1, img_r), (p2, img_g)])
    out_arr = np.array(out)
    # Panel 1: red
    assert tuple(out_arr[50, 50]) == (255, 0, 0)
    # Gutter between panels: grey background
    assert tuple(out_arr[115, 50]) == (128, 128, 128)
    # Panel 2: green
    assert tuple(out_arr[180, 50]) == (0, 255, 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_compositor.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `core/compositor.py`**

```python
"""Compose a SolvedPage + per-panel images into a single PIL.Image."""
from __future__ import annotations
from typing import Iterable
import numpy as np
from PIL import Image, ImageDraw
from .types import SolvedPage, SolvedPanel


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _arr_to_pil(arr: np.ndarray) -> Image.Image:
    if arr.dtype != np.uint8:
        arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def compose_page(page: SolvedPage, panel_images: Iterable[tuple[SolvedPanel, np.ndarray]]) -> Image.Image:
    """Paste each panel image onto the page canvas and draw its border (if any).

    `panel_images` yields (SolvedPanel, HxWx3 float32 in [0,1] or uint8) pairs.
    """
    canvas = Image.new("RGB", (page.page_width, page.page_height), _hex_to_rgb(page.background))

    for panel, img_arr in panel_images:
        pil = _arr_to_pil(img_arr)
        # In M1 every panel is rect; paste directly.
        canvas.paste(pil, panel.bbox_topleft)

        if panel.border["width_px"] > 0:
            draw = ImageDraw.Draw(canvas)
            x0, y0 = panel.bbox_topleft
            w, h = panel.bbox_size
            color = _hex_to_rgb(panel.border["color"])
            width = panel.border["width_px"]
            draw.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], outline=color, width=width)

    return canvas
```

- [ ] **Step 4: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_compositor.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/core/compositor.py \
        tk_comfyui_batch_image/tests/test_compositor.py
git commit -m "feat(core): add rect-only page compositor with border"
```

---

## Task 11: `nodes/script_loader.py` — ComfyUI input node

**Files:**
- Create: `tk_comfyui_batch_image/nodes/script_loader.py`
- Create: `tk_comfyui_batch_image/tests/conftest.py`
- Create: `tk_comfyui_batch_image/tests/test_script_loader.py`

- [ ] **Step 1: Write `conftest.py` with ComfyUI folder_paths stub**

```python
# tests/conftest.py
"""Shared fixtures for node-level tests.

ComfyUI isn't importable in CI, so we stub the parts our nodes touch.
"""
import sys
import types
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def stub_folder_paths(monkeypatch, tmp_path: Path):
    """Provide a minimal `folder_paths` module used by ComfyUI nodes for
    input / output directory lookup."""
    input_dir = tmp_path / "input" / "comics"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    mod = types.ModuleType("folder_paths")
    mod.get_input_directory = lambda: str(tmp_path / "input")
    mod.get_output_directory = lambda: str(output_dir)
    # ComfyUI has get_filename_list for widget dropdowns
    def _ls(dir_name: str):
        p = tmp_path / dir_name
        return [f.name for f in p.glob("**/*") if f.is_file()] if p.exists() else []
    mod.get_filename_list = _ls
    monkeypatch.setitem(sys.modules, "folder_paths", mod)
    yield {"input_dir": tmp_path / "input", "output_dir": output_dir}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_script_loader.py
import json
import shutil
from pathlib import Path

import pytest
from tk_comfyui_batch_image.nodes.script_loader import ComicScriptLoader

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def test_input_types_declares_modes():
    inputs = ComicScriptLoader.INPUT_TYPES()
    required = inputs["required"]
    assert "mode" in required
    assert set(required["mode"][0]) == {"file", "path", "inline"}
    optional = inputs.get("optional", {})
    assert "json_file" in optional
    assert "json_path" in optional
    assert "json_text" in optional


def test_return_types_include_comic_script_and_summary():
    assert "COMIC_SCRIPT" in ComicScriptLoader.RETURN_TYPES
    assert "STRING" in ComicScriptLoader.RETURN_TYPES


def test_load_from_inline_mode():
    node = ComicScriptLoader()
    text = (FIXTURES / "minimal.json").read_text(encoding="utf-8")
    script, summary = node.load(mode="inline", json_text=text, json_file="", json_path="")
    assert script.job_id == "min"
    assert "1 page" in summary
    assert "1 panel" in summary


def test_load_from_path_mode(tmp_path: Path):
    target = tmp_path / "script.json"
    shutil.copy(FIXTURES / "basic.json", target)
    node = ComicScriptLoader()
    script, summary = node.load(mode="path", json_text="", json_file="", json_path=str(target))
    assert script.job_id == "basic"
    assert "2 pages" in summary
    assert "4 panels" in summary


def test_load_from_file_mode(stub_folder_paths):
    dst = stub_folder_paths["input_dir"] / "comics" / "basic.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "basic.json", dst)
    node = ComicScriptLoader()
    script, summary = node.load(
        mode="file", json_file="comics/basic.json", json_text="", json_path="",
    )
    assert script.job_id == "basic"


def test_invalid_json_raises_with_readable_message():
    node = ComicScriptLoader()
    text = (FIXTURES / "minimal.json").read_text(encoding="utf-8")
    data = json.loads(text)
    del data["version"]
    node = ComicScriptLoader()
    with pytest.raises(Exception) as exc:
        node.load(mode="inline", json_text=json.dumps(data),
                  json_file="", json_path="")
    assert "validation failed" in str(exc.value).lower() or "version" in str(exc.value)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_script_loader.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Write `nodes/script_loader.py`**

```python
"""ComicScriptLoader — load + validate + normalize comic script JSON."""
from __future__ import annotations
import json
from pathlib import Path

from ..core.normalizer import normalize_script
from ..core.types import COMIC_SCRIPT_TYPE, SolvedScript
from ..core.validator import validate_schema


def _summary(script: SolvedScript) -> str:
    total_panels = sum(len(p.panels) for p in script.pages)
    page_word = "page" if len(script.pages) == 1 else "pages"
    panel_word = "panel" if total_panels == 1 else "panels"
    return (
        f"job_id={script.job_id}  "
        f"{len(script.pages)} {page_word}, {total_panels} {panel_word}  "
        f"reading={script.reading_direction}"
    )


def _resolve_file_mode(json_file: str) -> Path:
    import folder_paths  # type: ignore  # ComfyUI-provided at runtime
    input_dir = Path(folder_paths.get_input_directory())
    candidate = (input_dir / json_file).resolve()
    if not str(candidate).startswith(str(input_dir.resolve())):
        raise ValueError(f"json_file escapes input directory: {json_file}")
    if not candidate.exists():
        raise FileNotFoundError(f"json_file not found: {candidate}")
    return candidate


class ComicScriptLoader:
    """Load a comic script JSON, validate it, and emit a SolvedScript."""

    CATEGORY = "comic/io"
    FUNCTION = "load"
    RETURN_TYPES = (COMIC_SCRIPT_TYPE, "STRING")
    RETURN_NAMES = ("comic_script", "summary")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["file", "path", "inline"], {"default": "file"}),
            },
            "optional": {
                "json_file": ("STRING", {"default": "", "multiline": False,
                                         "tooltip": "Relative path inside ComfyUI input dir; used when mode=file."}),
                "json_path": ("STRING", {"default": "", "multiline": False,
                                         "tooltip": "Absolute / relative path to JSON; used when mode=path."}),
                "json_text": ("STRING", {"default": "", "multiline": True,
                                         "tooltip": "Inline JSON text; used when mode=inline."}),
            },
        }

    def load(self, mode: str, json_file: str = "", json_path: str = "", json_text: str = ""):
        if mode == "inline":
            raw = json_text
        elif mode == "path":
            if not json_path:
                raise ValueError("mode=path requires json_path")
            raw = Path(json_path).read_text(encoding="utf-8")
        elif mode == "file":
            if not json_file:
                raise ValueError("mode=file requires json_file")
            raw = _resolve_file_mode(json_file).read_text(encoding="utf-8")
        else:
            raise ValueError(f"unknown mode: {mode}")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}") from e

        validate_schema(data)
        script = normalize_script(data)
        return script, _summary(script)
```

- [ ] **Step 5: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_script_loader.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/nodes/script_loader.py \
        tk_comfyui_batch_image/tests/conftest.py \
        tk_comfyui_batch_image/tests/test_script_loader.py
git commit -m "feat(nodes): add ComicScriptLoader (file/path/inline modes)"
```

---

## Task 12: `nodes/batch_generator.py` — ComicBatchGenerator

**Files:**
- Create: `tk_comfyui_batch_image/nodes/batch_generator.py`
- Create: `tk_comfyui_batch_image/tests/test_batch_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_batch_generator.py
import json
from pathlib import Path
import numpy as np
import torch
import pytest

from tk_comfyui_batch_image.core.normalizer import normalize_script
from tk_comfyui_batch_image.core.sampler_runner import SamplerBackend
from tk_comfyui_batch_image.nodes.batch_generator import ComicBatchGenerator

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


class RecordingBackend(SamplerBackend):
    """Deterministic grey-image backend that records every call."""

    def __init__(self):
        self.n_sample_calls = 0

    def encode(self, clip, text): return ("c", text)
    def empty_latent(self, w, h, batch_size=1):
        return {"w": w, "h": h}
    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               cond_pos, cond_neg, latent, denoise):
        self.n_sample_calls += 1
        return latent
    def vae_decode(self, vae, samples):
        h, w = samples["h"], samples["w"]
        return np.full((h, w, 3), 0.5, dtype=np.float32)


def _gen(node, script, backend, out_dir, on_failure="halt"):
    return node.generate(
        comic_script=script, model="M", clip="C", vae="V",
        positive_suffix="", negative_suffix="",
        sampler_name="euler", scheduler="normal", steps=10, cfg=7.0, denoise=1.0,
        on_failure=on_failure, retries=1,
        _backend=backend, _out_dir=out_dir,
    )


def test_generator_returns_image_tensor_for_all_panels(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    backend = RecordingBackend()
    images, pass_script, log = _gen(ComicBatchGenerator(), script, backend, tmp_path)
    assert isinstance(images, torch.Tensor)
    assert images.dim() == 4 and images.shape[-1] == 3   # (N, H, W, 3)
    assert images.shape[0] == 4   # 3 panels in page 1 + 1 in page 2
    assert backend.n_sample_calls == 4


def test_generator_cache_skips_when_hash_matches(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    backend1 = RecordingBackend()
    _gen(ComicBatchGenerator(), script, backend1, tmp_path)
    assert backend1.n_sample_calls == 4

    backend2 = RecordingBackend()
    _gen(ComicBatchGenerator(), script, backend2, tmp_path)
    assert backend2.n_sample_calls == 0   # all cached


def test_generator_invalidates_cache_when_prompt_changes(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    _gen(ComicBatchGenerator(), script, RecordingBackend(), tmp_path)

    # modify a prompt in one panel
    data["pages"][0]["panels"][1]["scene_prompt"]["positive"] = "CHANGED"
    script2 = normalize_script(data)
    backend = RecordingBackend()
    _gen(ComicBatchGenerator(), script2, backend, tmp_path)
    assert backend.n_sample_calls == 1   # only the changed panel


class FlakyBackend(RecordingBackend):
    def __init__(self, fail_on_panel: int, fail_times: int):
        super().__init__()
        self.fail_on = fail_on_panel
        self.fail_times = fail_times
        self.panel_seen = -1

    def sample(self, *args, **kwargs):
        self.panel_seen += 1
        if self.panel_seen == self.fail_on and self.fail_times > 0:
            self.fail_times -= 1
            self.panel_seen -= 1      # retry counts same panel
            raise RuntimeError("boom")
        return super().sample(*args, **kwargs)


def test_retry_then_skip_mode_tolerates_transient_failure(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    backend = FlakyBackend(fail_on_panel=1, fail_times=1)
    images, _, log = _gen(ComicBatchGenerator(), script, backend, tmp_path,
                          on_failure="retry_then_skip")
    assert images.shape[0] == 4
    assert "retry" in log.lower()


def test_halt_mode_raises_on_failure(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    backend = FlakyBackend(fail_on_panel=0, fail_times=5)
    with pytest.raises(RuntimeError):
        _gen(ComicBatchGenerator(), script, backend, tmp_path, on_failure="halt")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_batch_generator.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `nodes/batch_generator.py`**

```python
"""ComicBatchGenerator — inner for-loop that generates every panel."""
from __future__ import annotations
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image

from ..core.cache_manager import manifest_matches, panel_hash, panel_paths, write_manifest
from ..core.sampler_runner import SamplerBackend, run_panel_sampler
from ..core.types import COMIC_SCRIPT_TYPE, SolvedPanel, SolvedScript


def _arr_to_pil(arr: np.ndarray) -> Image.Image:
    arr_u8 = np.clip(arr * 255.0, 0, 255).astype(np.uint8) if arr.dtype != np.uint8 else arr
    return Image.fromarray(arr_u8, mode="RGB")


def _pil_to_arr(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return arr


def _red_x(w: int, h: int) -> np.ndarray:
    arr = np.full((h, w, 3), 1.0, dtype=np.float32)
    # crude X in red
    for i in range(min(w, h)):
        arr[i, i] = [1.0, 0.0, 0.0]
        arr[i, w - 1 - i if w - 1 - i >= 0 else 0] = [1.0, 0.0, 0.0]
    return arr


class _ComfyUIBackend(SamplerBackend):
    """Thin adapter around ComfyUI's built-in nodes. Imported lazily."""

    def __init__(self):
        import nodes as comfy_nodes  # type: ignore
        self._enc = comfy_nodes.CLIPTextEncode()
        self._ks  = comfy_nodes.KSampler()
        self._el  = comfy_nodes.EmptyLatentImage()
        self._vd  = comfy_nodes.VAEDecode()

    def encode(self, clip, text):
        return self._enc.encode(clip, text)[0]

    def empty_latent(self, width, height, batch_size=1):
        return self._el.generate(width, height, batch_size)[0]

    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               cond_pos, cond_neg, latent, denoise):
        return self._ks.sample(model, seed, steps, cfg, sampler_name, scheduler,
                               cond_pos, cond_neg, latent, denoise)[0]

    def vae_decode(self, vae, samples):
        img_tensor = self._vd.decode(vae, samples)[0]  # (N, H, W, 3) float 0~1
        return img_tensor[0].cpu().numpy()


class ComicBatchGenerator:
    """Generate every panel in a script using an internal for-loop."""

    CATEGORY = "comic/core"
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE", COMIC_SCRIPT_TYPE, "STRING")
    RETURN_NAMES = ("generated_panels", "comic_script", "generation_log")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "comic_script": (COMIC_SCRIPT_TYPE,),
                "model":        ("MODEL",),
                "clip":         ("CLIP",),
                "vae":          ("VAE",),
                "sampler_name": ("STRING", {"default": "euler"}),
                "scheduler":    ("STRING", {"default": "normal"}),
                "steps":        ("INT",    {"default": 25, "min": 1, "max": 200}),
                "cfg":          ("FLOAT",  {"default": 7.0, "min": 0.0, "max": 30.0, "step": 0.1}),
                "denoise":      ("FLOAT",  {"default": 1.0, "min": 0.0, "max": 1.0,  "step": 0.01}),
                "on_failure":   (["retry_then_skip", "halt"], {"default": "retry_then_skip"}),
                "retries":      ("INT",    {"default": 2, "min": 0, "max": 10}),
            },
            "optional": {
                "positive_suffix": ("STRING", {"default": "", "multiline": True}),
                "negative_suffix": ("STRING", {"default": "", "multiline": True}),
            },
        }

    def _resolve_out_dir(self, job_id: str, override: Optional[Path] = None) -> Path:
        if override is not None:
            d = Path(override) / "comics" / job_id
        else:
            import folder_paths  # type: ignore
            d = Path(folder_paths.get_output_directory()) / "comics" / job_id
        (d / "panels").mkdir(parents=True, exist_ok=True)
        return d

    def _merge_widget_defaults(self, panel: SolvedPanel, widget: dict) -> SolvedPanel:
        """Apply widget-level sampler defaults when the script didn't specify.

        The normalizer already filled defaults from `default_sampler` in the
        JSON; the node-level widgets act as a LOWEST-priority fallback only if
        the JSON default_sampler is missing a key — which the schema forbids,
        so in practice this is a no-op. Implemented for safety.
        """
        merged = {**widget, **panel.sampler}
        panel.sampler = merged
        return panel

    def generate(
        self, comic_script: SolvedScript, model, clip, vae,
        sampler_name, scheduler, steps, cfg, denoise,
        on_failure, retries,
        positive_suffix: str = "", negative_suffix: str = "",
        _backend: Optional[SamplerBackend] = None,
        _out_dir: Optional[Path] = None,
    ):
        backend = _backend if _backend is not None else _ComfyUIBackend()
        out_dir = self._resolve_out_dir(comic_script.job_id, _out_dir)
        widget_defaults = {
            "sampler_name": sampler_name, "scheduler": scheduler,
            "steps": steps, "cfg": cfg, "denoise": denoise,
        }

        log_lines: list[str] = []
        images: list[np.ndarray] = []
        total_panels = sum(len(p.panels) for p in comic_script.pages)
        done = 0

        for page in comic_script.pages:
            for panel in page.panels:
                panel = self._merge_widget_defaults(panel, widget_defaults)
                if positive_suffix.strip():
                    panel.positive_prompt = (
                        f"{panel.positive_prompt}, {positive_suffix.strip()}"
                        if panel.positive_prompt else positive_suffix.strip()
                    )
                if negative_suffix.strip():
                    panel.negative_prompt = (
                        f"{panel.negative_prompt}, {negative_suffix.strip()}"
                        if panel.negative_prompt else negative_suffix.strip()
                    )

                paths = panel_paths(out_dir, panel)
                done += 1
                tag = f"[page {panel.page_index:02d}/{len(comic_script.pages):02d}] panel {panel.panel_index:02d} ({done}/{total_panels})"

                if manifest_matches(paths.manifest, panel):
                    img = _pil_to_arr(Image.open(paths.image))
                    log_lines.append(f"{tag} ... cached")
                    images.append(img)
                    continue

                img: Optional[np.ndarray] = None
                last_err: Optional[BaseException] = None
                for attempt in range(1 + retries):
                    t0 = time.time()
                    try:
                        img = run_panel_sampler(backend, model=model, clip=clip, vae=vae, panel=panel)
                        log_lines.append(f"{tag} ... generated ({time.time() - t0:.1f}s)"
                                         + (f" retry#{attempt}" if attempt else ""))
                        break
                    except Exception as e:   # noqa: BLE001
                        last_err = e
                        log_lines.append(f"{tag} ... FAILED attempt {attempt + 1}: {e}")
                        continue

                if img is None:
                    if on_failure == "halt":
                        raise RuntimeError(f"panel generation failed: {tag}") from last_err
                    # retry_then_skip
                    img = _red_x(*panel.bbox_size)
                    log_lines.append(f"{tag} ... skipped with placeholder")
                    images.append(img)
                    continue

                _arr_to_pil(img).save(paths.image, format="PNG")
                write_manifest(paths.manifest, panel_hash(panel))
                images.append(img)

        stacked = torch.from_numpy(np.stack(images, axis=0)).float()
        return stacked, comic_script, "\n".join(log_lines)
```

- [ ] **Step 4: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_batch_generator.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/nodes/batch_generator.py \
        tk_comfyui_batch_image/tests/test_batch_generator.py
git commit -m "feat(nodes): add ComicBatchGenerator with resume + retry"
```

---

## Task 13: `nodes/page_composer.py` — ComicPageComposer

**Files:**
- Create: `tk_comfyui_batch_image/nodes/page_composer.py`
- Create: `tk_comfyui_batch_image/tests/test_page_composer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_page_composer.py
import json
from pathlib import Path
import numpy as np
import torch
from PIL import Image

from tk_comfyui_batch_image.core.normalizer import normalize_script
from tk_comfyui_batch_image.nodes.page_composer import ComicPageComposer

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def _make_panel_stack(script) -> torch.Tensor:
    """Produce a solid-colour IMAGE batch matching each panel's bbox_size."""
    imgs = []
    for page in script.pages:
        for panel in page.panels:
            w, h = panel.bbox_size
            arr = np.full((h, w, 3), 0.5, dtype=np.float32)
            imgs.append(arr)
    # Pad to same H/W by placing each into a max-sized canvas
    max_h = max(a.shape[0] for a in imgs)
    max_w = max(a.shape[1] for a in imgs)
    padded = [np.pad(a, ((0, max_h - a.shape[0]), (0, max_w - a.shape[1]), (0, 0)),
                     constant_values=1.0) for a in imgs]
    return torch.from_numpy(np.stack(padded, axis=0)).float()


def test_compose_basic_script_yields_n_pages():
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    stack = _make_panel_stack(script)
    pages, bboxes_json, pass_panels = ComicPageComposer().compose(
        generated_panels=stack, comic_script=script, debug_overlay=False,
    )
    assert isinstance(pages, torch.Tensor)
    assert pages.shape[0] == 2   # 2 pages
    assert pages.shape[-1] == 3
    assert pages.shape[1] == script.pages[0].page_height
    assert pages.shape[2] == script.pages[0].page_width


def test_bboxes_json_includes_all_panels():
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    stack = _make_panel_stack(script)
    _, bboxes_json, _ = ComicPageComposer().compose(
        generated_panels=stack, comic_script=script, debug_overlay=False,
    )
    parsed = json.loads(bboxes_json)
    assert len(parsed["pages"]) == 2
    assert len(parsed["pages"][0]["panels"]) == 3
    p0 = parsed["pages"][0]["panels"][0]
    assert "bbox_topleft" in p0 and "bbox_size" in p0


def test_individual_panels_passthrough_preserves_order():
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    stack = _make_panel_stack(script)
    _, _, pass_panels = ComicPageComposer().compose(
        generated_panels=stack, comic_script=script, debug_overlay=False,
    )
    assert torch.equal(pass_panels, stack)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_page_composer.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `nodes/page_composer.py`**

```python
"""ComicPageComposer — assemble panels into full page images."""
from __future__ import annotations
import json
import numpy as np
import torch

from ..core.compositor import compose_page
from ..core.types import COMIC_SCRIPT_TYPE, SolvedScript


def _pil_to_tensor(img) -> np.ndarray:
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0


def _bboxes_metadata(script: SolvedScript) -> dict:
    return {
        "job_id": script.job_id,
        "reading_direction": script.reading_direction,
        "pages": [
            {
                "page_index": page.page_index,
                "page_width": page.page_width,
                "page_height": page.page_height,
                "panels": [
                    {
                        "panel_index": panel.panel_index,
                        "bbox_topleft": list(panel.bbox_topleft),
                        "bbox_size":    list(panel.bbox_size),
                        "shape_type":   panel.shape_type,
                    } for panel in page.panels
                ],
            } for page in script.pages
        ],
    }


class ComicPageComposer:
    CATEGORY = "comic/io"
    FUNCTION = "compose"
    RETURN_TYPES = ("IMAGE", "STRING", "IMAGE")
    RETURN_NAMES = ("composed_pages", "panel_bboxes_json", "individual_panels")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "generated_panels": ("IMAGE",),
                "comic_script":     (COMIC_SCRIPT_TYPE,),
                "debug_overlay":    ("BOOLEAN", {"default": False}),
            }
        }

    def compose(self, generated_panels: torch.Tensor, comic_script: SolvedScript,
                debug_overlay: bool):
        panels_np = generated_panels.cpu().numpy()   # (N, Hmax, Wmax, 3)

        out_pages: list[np.ndarray] = []
        idx = 0
        for page in comic_script.pages:
            panel_imgs: list[tuple] = []
            for panel in page.panels:
                raw = panels_np[idx]
                w, h = panel.bbox_size
                cropped = raw[:h, :w, :]   # matching what BatchGenerator placed (top-left of padding)
                panel_imgs.append((panel, cropped))
                idx += 1
            pil = compose_page(page, panel_imgs)
            out_pages.append(_pil_to_tensor(pil))

        # Pad composed pages to same shape if sizes differ (M1: all same)
        max_h = max(p.shape[0] for p in out_pages)
        max_w = max(p.shape[1] for p in out_pages)
        padded = [np.pad(p, ((0, max_h - p.shape[0]), (0, max_w - p.shape[1]), (0, 0)),
                         constant_values=1.0) for p in out_pages]
        pages_tensor = torch.from_numpy(np.stack(padded, axis=0)).float()

        bboxes = json.dumps(_bboxes_metadata(comic_script), indent=2, ensure_ascii=False)
        return pages_tensor, bboxes, generated_panels
```

- [ ] **Step 4: Run tests**

Run: `pytest tk_comfyui_batch_image/tests/test_page_composer.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tk_comfyui_batch_image/nodes/page_composer.py \
        tk_comfyui_batch_image/tests/test_page_composer.py
git commit -m "feat(nodes): add ComicPageComposer (rect + bbox metadata)"
```

---

## Task 14: End-to-end integration + example workflow

**Files:**
- Create: `tk_comfyui_batch_image/tests/test_integration_e2e.py`
- Create: `tk_comfyui_batch_image/examples/workflows/m1_basic_vertical_stack.json`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_integration_e2e.py
"""End-to-end: loader → generator → composer with the basic.json fixture."""
from pathlib import Path
import numpy as np
import torch

from tk_comfyui_batch_image.nodes.script_loader import ComicScriptLoader
from tk_comfyui_batch_image.nodes.batch_generator import ComicBatchGenerator
from tk_comfyui_batch_image.nodes.page_composer import ComicPageComposer
from tk_comfyui_batch_image.core.sampler_runner import SamplerBackend

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


class GreyBackend(SamplerBackend):
    def encode(self, clip, text): return ("c", text)
    def empty_latent(self, w, h, batch_size=1): return {"w": w, "h": h}
    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               cond_pos, cond_neg, latent, denoise): return latent
    def vae_decode(self, vae, samples):
        h, w = samples["h"], samples["w"]
        return np.full((h, w, 3), 0.5, dtype=np.float32)


def test_full_pipeline_basic_script(tmp_path: Path):
    loader = ComicScriptLoader()
    text = (FIXTURES / "basic.json").read_text(encoding="utf-8")
    script, summary = loader.load(mode="inline", json_text=text,
                                  json_file="", json_path="")

    gen = ComicBatchGenerator()
    panels, pass_script, log = gen.generate(
        comic_script=script, model="M", clip="C", vae="V",
        sampler_name="euler", scheduler="normal", steps=10, cfg=7.0, denoise=1.0,
        on_failure="halt", retries=0,
        positive_suffix="", negative_suffix="",
        _backend=GreyBackend(), _out_dir=tmp_path,
    )

    composer = ComicPageComposer()
    pages, bboxes_json, pass_panels = composer.compose(
        generated_panels=panels, comic_script=pass_script, debug_overlay=False,
    )

    # 2 pages of same size
    assert pages.shape[0] == 2
    # all panels generated
    assert panels.shape[0] == 4
    # rerun without changes → everything cached
    gen2 = ComicBatchGenerator()
    panels2, _, log2 = gen2.generate(
        comic_script=script, model="M", clip="C", vae="V",
        sampler_name="euler", scheduler="normal", steps=10, cfg=7.0, denoise=1.0,
        on_failure="halt", retries=0,
        positive_suffix="", negative_suffix="",
        _backend=GreyBackend(), _out_dir=tmp_path,
    )
    assert "cached" in log2
    assert torch.allclose(panels, panels2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tk_comfyui_batch_image/tests/test_integration_e2e.py -v`
Expected: should PASS (all upstream tasks done) — run anyway to confirm wiring is correct.

- [ ] **Step 3: Write example workflow JSON**

`examples/workflows/m1_basic_vertical_stack.json`:
```json
{
  "last_node_id": 7,
  "last_link_id": 8,
  "nodes": [
    { "id": 1, "type": "CheckpointLoaderSimple", "pos": [40, 100],
      "inputs": [], "outputs": [{"name":"MODEL","type":"MODEL","links":[1]},
                                 {"name":"CLIP","type":"CLIP","links":[2]},
                                 {"name":"VAE","type":"VAE","links":[3]}],
      "widgets_values": ["realistic_vision.safetensors"] },
    { "id": 2, "type": "ComicScriptLoader", "pos": [40, 300],
      "inputs": [],
      "outputs": [{"name":"comic_script","type":"COMIC_SCRIPT","links":[4]},
                  {"name":"summary","type":"STRING","links":null}],
      "widgets_values": ["file", "comics/basic.json", "", ""] },
    { "id": 3, "type": "ComicBatchGenerator", "pos": [400, 150],
      "inputs": [
        {"name":"comic_script","type":"COMIC_SCRIPT","link":4},
        {"name":"model","type":"MODEL","link":1},
        {"name":"clip","type":"CLIP","link":2},
        {"name":"vae","type":"VAE","link":3}
      ],
      "outputs": [
        {"name":"generated_panels","type":"IMAGE","links":[5]},
        {"name":"comic_script","type":"COMIC_SCRIPT","links":[6]},
        {"name":"generation_log","type":"STRING","links":null}
      ],
      "widgets_values": ["euler","normal",25,7.0,1.0,"retry_then_skip",2,"",""] },
    { "id": 4, "type": "ComicPageComposer", "pos": [800, 150],
      "inputs": [
        {"name":"generated_panels","type":"IMAGE","link":5},
        {"name":"comic_script","type":"COMIC_SCRIPT","link":6}
      ],
      "outputs": [
        {"name":"composed_pages","type":"IMAGE","links":[7]},
        {"name":"panel_bboxes_json","type":"STRING","links":null},
        {"name":"individual_panels","type":"IMAGE","links":null}
      ],
      "widgets_values": [false] },
    { "id": 5, "type": "SaveImage", "pos": [1200, 150],
      "inputs": [{"name":"images","type":"IMAGE","link":7}],
      "widgets_values": ["comic/page"] }
  ],
  "links": [
    [1,1,0,3,1,"MODEL"],
    [2,1,1,3,2,"CLIP"],
    [3,1,2,3,3,"VAE"],
    [4,2,0,3,0,"COMIC_SCRIPT"],
    [5,3,0,4,0,"IMAGE"],
    [6,3,1,4,1,"COMIC_SCRIPT"],
    [7,4,0,5,0,"IMAGE"]
  ],
  "version": 0.4
}
```

- [ ] **Step 4: Run full test suite**

Run: `pytest tk_comfyui_batch_image/tests/ -v`
Expected: all tests pass (expected ~45–55 tests across 10 files).

- [ ] **Step 5: Run linter**

Run: `ruff check tk_comfyui_batch_image`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add tk_comfyui_batch_image/tests/test_integration_e2e.py \
        tk_comfyui_batch_image/examples/workflows/m1_basic_vertical_stack.json
git commit -m "test: add E2E integration test + example ComfyUI workflow"
```

---

## Task 15: README update with M1 usage

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Overwrite README with M1 instructions**

```markdown
# tk_comfyui_batch_image

ComfyUI custom node set for batch comic-page generation from a JSON script.

**Status:** M1 — Rectangle vertical-stack. See `docs/superpowers/specs/2026-04-23-comfyui-comic-batch-node-design.md` for the full design; `docs/superpowers/plans/` for milestones.

## Install

Clone this repo into `ComfyUI/custom_nodes/`, then:

```bash
pip install -e .[dev]
```

Restart ComfyUI.

## Nodes

| Node | Purpose |
|---|---|
| `Comic Script Loader` | Load + validate JSON; emits `COMIC_SCRIPT`. Modes: `file` / `path` / `inline`. |
| `Comic Batch Generator` | Inner for-loop over panels. Connect `MODEL / CLIP / VAE`; no KSampler needed. Supports resume via panel-hash cache. |
| `Comic Page Composer` | Assemble panels into full pages. Outputs composed IMAGE batch + bbox metadata + pass-through panels. |

## Example workflow

Drop `examples/workflows/m1_basic_vertical_stack.json` into ComfyUI.
Place `basic.json` (see `tests/fixtures/scripts/`) at `ComfyUI/input/comics/basic.json`.

## Running tests

```bash
pytest tk_comfyui_batch_image/tests/ -v
ruff check tk_comfyui_batch_image
```

## Current limitations (M1)

- Shapes: rectangle only (no `split` / `polygon` yet → M3/M4)
- Layout modes: `vertical_stack` only (no `custom_grid` yet → M3)
- No debug overlay (→ M5)
- No standalone JSON-validation CLI (→ M2)
- No SKILL.md skill package for AI script generation (→ M2)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document M1 nodes + install + usage"
```

---

## Self-Review Checklist

Spec-coverage (M1 scope only):
- §3.1 three nodes → Tasks 11–13 ✅
- §3.3 core modules → Tasks 2–10 ✅
- §4 Book/Page/Panel schema (rect only) → Task 3 ✅
- §4.5 inheritance (prompt 4-layer, sampler merge, border inherit) → Task 7 (normalizer) + Task 5 (prompt_builder) ✅
- §5.1–5.2 vertical_stack + rect bbox → Task 6 ✅
- §6.1 inner for-loop → Task 12 ✅
- §6.2 panel hash resume → Task 8 + Task 12 ✅
- §6.3 retry_then_skip / halt → Task 12 tests ✅
- §7.1–7.2 rect paste + border → Task 10 ✅
- §7.3 outputs (composed / individual / bboxes) → Task 13 ✅
- §8.1 Layer 1 validation → Task 4 ✅
- §10 tests across modules → each task has tests ✅
- §13 M1 scope → matches exactly ✅

Deferred (NOT in M1, which is correct per plan scope):
- §4.4 `shape_group` / `polygon` → M3 / M4
- §5.3 split sisters / §5.4 aa polygon mask → M3
- §7.2 debug overlay → M5 (placeholder bool input present; implementation trivial in M5)
- §8.1 Layer 2 semantic validation beyond layout_solver's overflow check → M2
- §8.2 custom error format → M2 (current jsonschema errors are readable enough)
- §8.3 standalone CLI → M2
- §9 SKILL.md package → M2

Placeholder scan: no "TBD", "TODO", "add appropriate error handling", or "similar to task N" appear. All code blocks are complete.

Type consistency: `SolvedPanel`, `SolvedPage`, `SolvedScript`, `COMIC_SCRIPT_TYPE` names used identically across Tasks 2, 7, 11, 12, 13. `PanelPaths.image / .manifest` used consistently in Tasks 8 and 12. `SamplerBackend` protocol members (`encode`, `empty_latent`, `sample`, `vae_decode`) used identically in Tasks 9, 12, 14.

---

## Execution Handoff

Plan complete and saved to [docs/superpowers/plans/2026-04-23-comic-batch-m1-foundation.md](../plans/2026-04-23-comic-batch-m1-foundation.md).

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
