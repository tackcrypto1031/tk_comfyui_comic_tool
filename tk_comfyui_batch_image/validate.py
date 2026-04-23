"""Standalone CLI for validating comic script JSONs.

Usage:
    python -m tk_comfyui_batch_image.validate <file1> [file2 ...] [options]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
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


def _file_result_dict(path: Path, status: str, errors: list[CheckError], info: dict | None) -> dict:
    d = {
        "path": str(path),
        "status": status,
        "errors": [asdict(e) for e in errors],
    }
    if info is not None:
        d["info"] = info
    return d


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
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of human-readable text")
    args = parser.parse_args(argv)

    if not args.files:
        parser.print_usage(sys.stderr)
        return 2

    results: list[dict] = []
    any_fail = False

    for raw in args.files:
        path = Path(raw)
        if not path.exists():
            if args.json:
                results.append({"path": str(path), "status": "fail",
                                "errors": [{"layer": 0, "path": "<io>",
                                            "message": "file not found", "hint": None}]})
                any_fail = True
                continue
            else:
                print(f"✗ {path}  (file not found)", file=sys.stderr)
                return 3
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError) as e:
            if args.json:
                results.append({"path": str(path), "status": "fail",
                                "errors": [{"layer": 0, "path": "<io>",
                                            "message": f"I/O or JSON parse error: {e}",
                                            "hint": None}]})
                any_fail = True
                continue
            else:
                print(f"✗ {path}  (I/O or JSON parse error: {e})", file=sys.stderr)
                return 3

        errors = collect_errors(data)
        if errors:
            any_fail = True
            if args.json:
                results.append(_file_result_dict(path, "fail", errors, None))
            else:
                _print_file_human(path, "fail", errors, None)
        else:
            info = {"version": data.get("version"), **_summarize_file(path, data)}
            if args.json:
                results.append(_file_result_dict(path, "ok", [], info))
            else:
                _print_file_human(path, "ok", [], info)

    if args.json:
        summary = {
            "total": len(results),
            "ok":   sum(1 for r in results if r["status"] == "ok"),
            "fail": sum(1 for r in results if r["status"] == "fail"),
        }
        print(json.dumps({"summary": summary, "files": results},
                         indent=2, ensure_ascii=False))

    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
