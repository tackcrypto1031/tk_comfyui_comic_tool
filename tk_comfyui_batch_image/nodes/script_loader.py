"""ComicScriptLoader — load + validate + normalize comic script JSON."""
from __future__ import annotations

import json
from pathlib import Path

from ..core.normalizer import normalize_script
from ..core.types import COMIC_SCRIPT_TYPE, SolvedScript
from ..core.validator import validate


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

        validate(data)
        script = normalize_script(data)
        return script, _summary(script)
