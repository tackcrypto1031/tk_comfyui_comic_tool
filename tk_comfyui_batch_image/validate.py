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


def _ensure_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 if the current encoding can't handle it."""
    import contextlib
    import io
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            with contextlib.suppress(Exception):
                stream.reconfigure(encoding="utf-8", errors="replace")
        elif hasattr(stream, "buffer"):
            setattr(sys, stream_name,
                    io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
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
