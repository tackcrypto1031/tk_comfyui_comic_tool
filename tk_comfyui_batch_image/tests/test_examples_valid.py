"""Each example's output.json must pass the M2 validator."""
import json
from pathlib import Path

import pytest

from tk_comfyui_batch_image.core.validator import validate

EXAMPLES_ROOT = (
    Path(__file__).resolve().parent.parent.parent
    / "docs" / "skills" / "comic-script-authoring" / "examples"
)


def _example_dirs():
    if not EXAMPLES_ROOT.exists():
        return []
    return sorted(d for d in EXAMPLES_ROOT.iterdir() if d.is_dir())


@pytest.mark.parametrize("example_dir", _example_dirs(), ids=lambda d: d.name)
def test_example_output_json_is_valid(example_dir):
    output = example_dir / "output.json"
    assert output.exists(), f"{example_dir.name} is missing output.json"
    data = json.loads(output.read_text(encoding="utf-8"))
    validate(data)   # raises ValidationError if bad


@pytest.mark.parametrize("example_dir", _example_dirs(), ids=lambda d: d.name)
def test_example_has_screenplay(example_dir):
    screenplay = example_dir / "screenplay.md"
    assert screenplay.exists(), f"{example_dir.name} is missing screenplay.md"
    assert screenplay.read_text(encoding="utf-8").strip(), \
        f"{example_dir.name}/screenplay.md is empty"
