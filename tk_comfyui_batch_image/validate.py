"""Standalone CLI for validating comic script JSONs.

Usage:
    python -m tk_comfyui_batch_image.validate <file1> [file2 ...] [options]
"""
from __future__ import annotations

import argparse
import contextlib
import io
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


def _file_result_dict(path: Path, status: str, errors: list[CheckError],
                      info: dict | None, truncated: bool = False) -> dict:
    d = {
        "path": str(path),
        "status": status,
        "errors": [asdict(e) for e in errors],
        "truncated": truncated,
    }
    if info is not None:
        d["info"] = info
    return d


def _ensure_utf8_stdio() -> None:
    """Make stdout/stderr UTF-8 on Windows terminals (cp950 by default)
    so ✓/✗ characters don't raise UnicodeEncodeError. No-op on streams
    already encoding UTF-8 or lacking `reconfigure`."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(AttributeError, io.UnsupportedOperation, OSError):
                reconfigure(encoding="utf-8")
            continue
        buf = getattr(stream, "buffer", None)
        if buf is None:
            continue
        with contextlib.suppress(AttributeError, io.UnsupportedOperation, OSError):
            setattr(sys, name, io.TextIOWrapper(buf, encoding="utf-8", line_buffering=True))


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="python -m tk_comfyui_batch_image.validate",
        description="Validate comic script JSON(s).",
    )
    parser.add_argument("files", nargs="*", help="JSON file(s) to validate")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of human-readable text")
    parser.add_argument("--max-errors", type=int, default=20, metavar="N",
                        help="Show at most N errors per file (default: 20)")
    args = parser.parse_args(argv)

    if not args.files:
        parser.print_usage(sys.stderr)
        return 2

    results: list[dict] = []
    ok_count = 0
    fail_count = 0

    for raw in args.files:
        path = Path(raw)

        if not path.exists():
            if args.json:
                results.append(_file_result_dict(
                    path, "fail",
                    [CheckError(layer=0, path="<io>", message="file not found")],
                    None, False,
                ))
                fail_count += 1
                continue
            print(f"✗ {path}  (file not found)", file=sys.stderr)
            return 3

        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError) as e:
            if args.json:
                results.append(_file_result_dict(
                    path, "fail",
                    [CheckError(layer=0, path="<io>",
                                message=f"I/O or JSON parse error: {e}")],
                    None, False,
                ))
                fail_count += 1
                continue
            print(f"✗ {path}  (I/O or JSON parse error: {e})", file=sys.stderr)
            return 3

        errors = collect_errors(data)
        if errors:
            fail_count += 1
            shown = errors[:args.max_errors]
            suppressed = max(0, len(errors) - args.max_errors)
            truncated = suppressed > 0
            if args.json:
                results.append(_file_result_dict(path, "fail", shown, None, truncated))
            else:
                _print_file_human(path, "fail", shown, None, suppressed)
        else:
            ok_count += 1
            info = {"version": data.get("version"), **_summarize_file(path, data)}
            if args.json:
                results.append(_file_result_dict(path, "ok", [], info, False))
            else:
                _print_file_human(path, "ok", [], info)

    if args.json:
        print(json.dumps({
            "summary": {"total": ok_count + fail_count,
                        "ok": ok_count, "fail": fail_count},
            "files": results,
        }, indent=2, ensure_ascii=False))
    elif len(args.files) > 1:
        print()
        print("---")
        total = ok_count + fail_count
        print(f"Summary: {total} files, {ok_count} ✓ ok, {fail_count} ✗ fail")

    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
