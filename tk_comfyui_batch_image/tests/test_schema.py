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
