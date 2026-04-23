# tests/conftest.py
"""Shared fixtures for node-level tests.

ComfyUI isn't importable in CI, so we stub the parts our nodes touch.
"""
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def stub_folder_paths(monkeypatch, tmp_path: Path):
    """Provide a minimal `folder_paths` module used by ComfyUI nodes for
    input / output directory lookup."""
    input_dir = tmp_path / "input" / "comics"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    mod = types.ModuleType("folder_paths")
    mod.get_input_directory = lambda: str(tmp_path / "input")
    mod.get_output_directory = lambda: str(output_dir)
    # ComfyUI has get_filename_list for widget dropdowns
    def _ls(dir_name: str):
        p = tmp_path / dir_name
        return [f.name for f in p.glob("**/*") if f.is_file()] if p.exists() else []
    mod.get_filename_list = _ls
    monkeypatch.setitem(sys.modules, "folder_paths", mod)
    yield {"input_dir": tmp_path / "input", "output_dir": output_dir}
