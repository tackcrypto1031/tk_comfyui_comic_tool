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
