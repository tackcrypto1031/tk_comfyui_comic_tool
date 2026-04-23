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
