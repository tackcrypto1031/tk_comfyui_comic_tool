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
