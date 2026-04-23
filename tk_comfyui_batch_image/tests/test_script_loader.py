# tests/test_script_loader.py
import json
import shutil
from pathlib import Path

import pytest

from tk_comfyui_batch_image.nodes.script_loader import ComicScriptLoader

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def test_input_types_declares_modes():
    inputs = ComicScriptLoader.INPUT_TYPES()
    required = inputs["required"]
    assert "mode" in required
    assert set(required["mode"][0]) == {"file", "path", "inline"}
    optional = inputs.get("optional", {})
    assert "json_file" in optional
    assert "json_path" in optional
    assert "json_text" in optional


def test_return_types_include_comic_script_and_summary():
    assert "COMIC_SCRIPT" in ComicScriptLoader.RETURN_TYPES
    assert "STRING" in ComicScriptLoader.RETURN_TYPES


def test_load_from_inline_mode():
    node = ComicScriptLoader()
    text = (FIXTURES / "minimal.json").read_text(encoding="utf-8")
    script, summary = node.load(mode="inline", json_text=text, json_file="", json_path="")
    assert script.job_id == "min"
    assert "1 page" in summary
    assert "1 panel" in summary


def test_load_from_path_mode(tmp_path: Path):
    target = tmp_path / "script.json"
    shutil.copy(FIXTURES / "basic.json", target)
    node = ComicScriptLoader()
    script, summary = node.load(mode="path", json_text="", json_file="", json_path=str(target))
    assert script.job_id == "basic"
    assert "2 pages" in summary
    assert "4 panels" in summary


def test_load_from_file_mode(stub_folder_paths):
    dst = stub_folder_paths["input_dir"] / "comics" / "basic.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "basic.json", dst)
    node = ComicScriptLoader()
    script, summary = node.load(
        mode="file", json_file="comics/basic.json", json_text="", json_path="",
    )
    assert script.job_id == "basic"


def test_invalid_json_raises_with_readable_message():
    node = ComicScriptLoader()
    text = (FIXTURES / "minimal.json").read_text(encoding="utf-8")
    data = json.loads(text)
    del data["version"]
    node = ComicScriptLoader()
    with pytest.raises(Exception) as exc:
        node.load(mode="inline", json_text=json.dumps(data),
                  json_file="", json_path="")
    assert "validation failed" in str(exc.value).lower() or "version" in str(exc.value)
