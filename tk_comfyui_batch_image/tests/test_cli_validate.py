"""Tests for the standalone validate CLI."""
import json
from pathlib import Path

from tk_comfyui_batch_image.validate import main


def _write(tmp_path: Path, name: str, body: dict | str) -> Path:
    p = tmp_path / name
    p.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return p


def _valid_minimal_book() -> dict:
    return {
        "version": "1.0", "job_id": "cli_test", "reading_direction": "ltr",
        "page_template": "custom", "page_width_px": 1080, "page_height_px": 1920,
        "bleed_px": 20, "gutter_px": 10, "page_background": "#FFFFFF", "base_seed": 0,
        "style_prompt":     {"positive": "", "negative": ""},
        "character_prompt": {"positive": "", "negative": ""},
        "default_sampler": {
            "sampler_name": "euler", "scheduler": "normal",
            "steps": 20, "cfg": 7.0, "denoise": 1.0},
        "default_border": {"width_px": 2, "color": "#000000", "style": "solid"},
        "pages": [{
            "page_index": 1,
            "page_prompt": {"positive": "", "negative": ""},
            "layout_mode": "vertical_stack",
            "panels": [{
                "panel_index": 1,
                "scene_prompt": {"positive": "s", "negative": ""},
                "width_px": 1040, "height_px": 600,
                "align": "center", "shape": {"type": "rect"},
            }],
        }],
    }


def test_cli_no_args_returns_exit_2(capsys):
    code = main([])
    assert code == 2
    out = capsys.readouterr()
    assert "usage" in (out.out + out.err).lower()


def test_cli_single_valid_file_exits_0(tmp_path, capsys):
    p = _write(tmp_path, "ok.json", _valid_minimal_book())
    code = main([str(p)])
    assert code == 0
    assert "✓" in capsys.readouterr().out


def test_cli_single_invalid_file_exits_1(tmp_path, capsys):
    book = _valid_minimal_book()
    book["pages"][0]["page_index"] = 5
    p = _write(tmp_path, "bad.json", book)
    code = main([str(p)])
    assert code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "[L2]" in out


def test_cli_missing_file_exits_3(tmp_path, capsys):
    code = main([str(tmp_path / "nope.json")])
    assert code == 3


def test_cli_unreadable_json_exits_3(tmp_path, capsys):
    p = _write(tmp_path, "broken.json", "{not json")
    code = main([str(p)])
    assert code == 3


def test_cli_json_output_structure_on_success(tmp_path, capsys):
    p = _write(tmp_path, "ok.json", _valid_minimal_book())
    code = main([str(p), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["summary"] == {"total": 1, "ok": 1, "fail": 0}
    assert len(payload["files"]) == 1
    f0 = payload["files"][0]
    assert f0["status"] == "ok"
    assert f0["errors"] == []
    assert f0["info"]["job_id"] == "cli_test"
    assert f0["info"]["page_count"] == 1
    assert f0["info"]["panel_count"] == 1


def test_cli_json_output_structure_on_failure(tmp_path, capsys):
    book = _valid_minimal_book()
    book["pages"][0]["page_index"] = 5
    p = _write(tmp_path, "bad.json", book)
    code = main([str(p), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["summary"] == {"total": 1, "ok": 0, "fail": 1}
    f0 = payload["files"][0]
    assert f0["status"] == "fail"
    assert len(f0["errors"]) >= 1
    err = f0["errors"][0]
    assert err["layer"] == 2
    assert err["path"] == "pages[0].page_index"
    assert "expected 1" in err["message"]


def test_cli_multi_file_mixed_exits_1_with_summary(tmp_path, capsys):
    ok = _write(tmp_path, "ok.json", _valid_minimal_book())
    bad_book = _valid_minimal_book()
    bad_book["pages"][0]["page_index"] = 5
    bad = _write(tmp_path, "bad.json", bad_book)
    code = main([str(ok), str(bad)])
    out = capsys.readouterr().out
    assert code == 1
    assert "✓" in out and "✗" in out
    assert "Summary" in out
    assert "2 files" in out
    assert "1 ✓" in out and "1 ✗" in out


def test_cli_max_errors_truncates_human(tmp_path, capsys):
    book = _valid_minimal_book()
    panel_template = book["pages"][0]["panels"][0]
    book["pages"] = [{
        "page_index": 100 + i,
        "page_prompt": {"positive": "", "negative": ""},
        "layout_mode": "vertical_stack",
        "panels": [{**panel_template, "panel_index": 1, "height_px": 100}],
    } for i in range(10)]
    p = _write(tmp_path, "many.json", book)
    code = main([str(p), "--max-errors", "3"])
    out = capsys.readouterr().out
    assert code == 1
    assert out.count("[L2]") == 3
    assert "7 more error" in out


def test_cli_max_errors_truncated_flag_in_json(tmp_path, capsys):
    book = _valid_minimal_book()
    panel_template = book["pages"][0]["panels"][0]
    book["pages"] = [{
        "page_index": 100 + i,
        "page_prompt": {"positive": "", "negative": ""},
        "layout_mode": "vertical_stack",
        "panels": [{**panel_template, "panel_index": 1, "height_px": 100}],
    } for i in range(5)]
    p = _write(tmp_path, "many.json", book)
    code = main([str(p), "--json", "--max-errors", "2"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    f0 = payload["files"][0]
    assert len(f0["errors"]) == 2
    assert f0["truncated"] is True
