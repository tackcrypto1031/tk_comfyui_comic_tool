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
