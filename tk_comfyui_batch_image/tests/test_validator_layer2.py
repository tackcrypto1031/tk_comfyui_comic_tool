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
