"""ComicScriptLoader — load + validate + normalize comic script JSON."""
from __future__ import annotations

import json
from pathlib import Path

from ..core.normalizer import normalize_script
from ..core.types import COMIC_SCRIPT_TYPE, SolvedScript
from ..core.validator import validate

MODE_OPTIONS = ["auto", "file", "path", "inline"]


def _summary(script: SolvedScript) -> str:
    total_panels = sum(len(p.panels) for p in script.pages)
    page_word = "page" if len(script.pages) == 1 else "pages"
    panel_word = "panel" if total_panels == 1 else "panels"
    return (
        f"job_id={script.job_id}  "
        f"{len(script.pages)} {page_word}, {total_panels} {panel_word}  "
        f"reading={script.reading_direction}"
    )


def _strip_surrounding_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1].strip()
    return s


def _list_input_json_files() -> list[str]:
    try:
        import folder_paths  # type: ignore
        input_dir = Path(folder_paths.get_input_directory())
    except Exception:
        return []
    if not input_dir.exists():
        return []
    return sorted(
        str(p.relative_to(input_dir)).replace("\\", "/")
        for p in input_dir.rglob("*.json")
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


def _resolve_auto_mode(json_file: str, json_path: str, json_text: str) -> str:
    filled = [name for name, val in
              (("inline", json_text), ("path", json_path), ("file", json_file))
              if val.strip()]
    if not filled:
        raise ValueError(
            "mode=auto: no input provided — fill json_file (dropdown), "
            "json_path (absolute path), or json_text (inline JSON)."
        )
    if len(filled) > 1:
        raise ValueError(
            f"mode=auto: multiple inputs filled ({', '.join(filled)}). "
            "Clear the ones you don't want, or set mode explicitly."
        )
    return filled[0]


class ComicScriptLoader:
    """Load a comic script JSON, validate it, and emit a SolvedScript."""

    CATEGORY = "comic/io"
    FUNCTION = "load"
    RETURN_TYPES = (COMIC_SCRIPT_TYPE, "STRING")
    RETURN_NAMES = ("comic_script", "summary")

    @classmethod
    def INPUT_TYPES(cls):
        json_files = _list_input_json_files()
        file_widget = (json_files, {"tooltip": "Pick a .json from ComfyUI input dir; used when mode=file."}) \
            if json_files else \
            ("STRING", {"default": "", "multiline": False,
                        "tooltip": "Relative path inside ComfyUI input dir; used when mode=file."})
        return {
            "required": {
                "mode": (MODE_OPTIONS, {"default": "auto",
                                        "tooltip": "auto = use whichever field below is filled."}),
            },
            "optional": {
                "json_file": file_widget,
                "json_path": ("STRING", {"default": "", "multiline": False,
                                         "tooltip": "Absolute / relative path to JSON (surrounding quotes are stripped); used when mode=path."}),
                "json_text": ("STRING", {"default": "", "multiline": True,
                                         "tooltip": "Inline JSON text; used when mode=inline."}),
            },
        }

    def load(self, mode: str, json_file: str = "", json_path: str = "", json_text: str = ""):
        json_path = _strip_surrounding_quotes(json_path)
        json_file = _strip_surrounding_quotes(json_file)

        if mode == "auto":
            mode = _resolve_auto_mode(json_file, json_path, json_text)

        if mode == "inline":
            raw = json_text
        elif mode == "path":
            if not json_path:
                raise ValueError("mode=path requires json_path")
            p = Path(json_path)
            if not p.exists():
                raise FileNotFoundError(
                    f"json_path not found: {p} "
                    "(tip: Windows 'Copy as Path' adds quotes — those are stripped automatically, "
                    "but check for typos or wrong drive letter.)"
                )
            raw = p.read_text(encoding="utf-8")
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
